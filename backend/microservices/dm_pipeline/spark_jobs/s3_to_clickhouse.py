"""PySpark job: S3 raw daily JSON -> ClickHouse (RAW/ODS/DM).

Reads a single daily raw file (`s3a://<bucket>/<object_key>`, one JSON
document `{date, stations: [...]}`) directly via the S3A connector — no
Postgres involved anymore (see data/pipeline_flow.md, "Принятые решения").
--dataset-type selects the target ClickHouse tables: "actual" writes
*_weather* tables (source: historical_fetcher via weather.actual.raw.created),
"forecast" writes *_forecast* tables (source: predict_fetcher, still
unbuilt, via weather.forecast.raw.created).

After writing the DM layer (in either branch) the dm_fct_forecast_error mart
is recomputed — inner join dm_fct_daily_weather x dm_fct_daily_forecast on
(wmo_index, day) for this business_date, signed and absolute error per
metric. If the other side doesn't exist yet the join is empty and nothing is
written; the mart backfills whenever the second side arrives (order of
actual/forecast doesn't matter).

Run by dm_pipeline_dag.py via spark-submit --master local[2] (no separate
Spark cluster, lean profile, one pod alongside Airflow standalone).
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

TABLE_CONFIG = {
    "actual": {
        "raw_table": "raw_weather_events",
        "ods_table": "ods_daily_weather",
        "dm_table": "dm_fct_daily_weather",
    },
    "forecast": {
        "raw_table": "raw_forecast_events",
        "ods_table": "ods_daily_forecast",
        "dm_table": "dm_fct_daily_forecast",
    },
}

ERROR_METRICS = ["temperature", "temp_min", "temp_max", "precipitation_mm"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--business-date", required=True, help="YYYY-MM-DD, observation_date/day")
    parser.add_argument("--trace-id", required=True)
    parser.add_argument(
        "--dataset-type", required=True, choices=sorted(TABLE_CONFIG), help="actual|forecast"
    )
    parser.add_argument("--bucket", required=True, help="S3 bucket holding the raw daily JSON file")
    parser.add_argument("--object-key", required=True, help="e.g. actual/date=1960-01-01.json")
    parser.add_argument("--source-name", required=True, help="producer of the raw file, e.g. historical_fetcher")
    parser.add_argument("--event-id", required=True, help="raw.created event_id (already made unique per date)")
    parser.add_argument("--event-created-at", required=True, help="ISO8601 created_at from the raw.created event")
    parser.add_argument("--result-path", required=True, help="where to write {record_count, business_date} JSON")
    return parser.parse_args()


def clickhouse_jdbc_url() -> str:
    host = os.environ["CLICKHOUSE_HOST"]
    port = os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")
    db = os.environ.get("CLICKHOUSE_DB", "weather")
    return f"jdbc:clickhouse://{host}:{port}/{db}"


def recompute_forecast_error(
    spark: SparkSession, *, business_date: str, clickhouse_props: dict
) -> None:
    """Recompute dm_fct_forecast_error for business_date from the current DM
    tables (both actual and forecast may or may not be populated yet)."""
    weather_df = spark.read.jdbc(
        url=clickhouse_jdbc_url(),
        table="dm_fct_daily_weather_current",
        properties=clickhouse_props,
    ).filter(F.col("day") == business_date)
    forecast_df = spark.read.jdbc(
        url=clickhouse_jdbc_url(),
        table="dm_fct_daily_forecast_current",
        properties=clickhouse_props,
    ).filter(F.col("day") == business_date)

    joined = weather_df.alias("w").join(
        forecast_df.alias("f"),
        on=(F.col("w.wmo_index") == F.col("f.wmo_index")) & (F.col("w.day") == F.col("f.day")),
        how="inner",
    )

    if joined.take(1) == []:
        return

    error_cols = []
    for metric in ERROR_METRICS:
        error_cols.append((F.col(f"f.{metric}") - F.col(f"w.{metric}")).alias(f"{metric}_error"))
        error_cols.append(
            F.abs(F.col(f"f.{metric}") - F.col(f"w.{metric}")).alias(f"{metric}_abs_error")
        )

    error_out = joined.select(
        F.col("w.wmo_index").alias("wmo_index"),
        F.col("w.day").alias("day"),
        *error_cols,
        F.col("w.trace_id").alias("actual_trace_id"),
        F.col("f.trace_id").alias("forecast_trace_id"),
        F.current_timestamp().alias("ingested_at"),
    )
    error_out.write.mode("append").jdbc(
        url=clickhouse_jdbc_url(), table="dm_fct_forecast_error", properties=clickhouse_props
    )


def main() -> None:
    args = parse_args()
    table_config = TABLE_CONFIG[args.dataset_type]

    spark = (
        SparkSession.builder.appName(f"dm_pipeline-{args.trace_id}")
        .master("local[2]")
        .config("spark.hadoop.fs.s3a.endpoint", os.environ["S3_ENDPOINT_URL"])
        .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"])
        .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"])
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config(
            "spark.hadoop.fs.s3a.connection.ssl.enabled",
            os.environ.get("S3_SSL_ENABLED", "true"),
        )
        .getOrCreate()
    )

    clickhouse_props = {
        "user": os.environ.get("CLICKHOUSE_USER", "default"),
        "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
        "driver": "com.clickhouse.jdbc.ClickHouseDriver",
    }

    # The raw file is a single JSON document {date, stations: [...]}, not
    # JSON-lines — multiLine is required or Spark reads it as truncated junk.
    raw_doc_df = spark.read.option("multiLine", "true").json(
        f"s3a://{args.bucket}/{args.object_key}"
    )
    stations_df = raw_doc_df.select(
        F.col("date").alias("observation_date"),
        F.explode("stations").alias("station"),
    )

    record_count = stations_df.count()

    ingested_at_col = F.current_timestamp()
    trace_id_lit = F.lit(args.trace_id)
    # Parsed in Python (not via Spark's to_timestamp + a fixed format
    # string) because the ISO8601 created_at from the raw.created event may
    # or may not carry fractional seconds, and to_timestamp silently returns
    # null on a format mismatch instead of erroring — which slipped a NULL
    # into a NOT NULL ClickHouse column on the first live run.
    event_created_at_dt = datetime.fromisoformat(args.event_created_at.replace("Z", "+00:00"))
    event_created_at_col = F.lit(event_created_at_dt.strftime("%Y-%m-%d %H:%M:%S")).cast(
        "timestamp"
    )

    # RAW: аудит-зеркало исходных station-строк для этого business_date.
    raw_out = stations_df.select(
        F.lit(args.source_name).alias("source_name"),
        F.col("observation_date"),
        F.col("station.wmo_index").cast("string").alias("wmo_index"),
        F.col("station.name").alias("station_name"),
        F.col("station.country").alias("country"),
        F.col("station.min_temp").alias("min_temp"),
        F.col("station.avg_temp").alias("avg_temp"),
        F.col("station.max_temp").alias("max_temp"),
        F.col("station.precipitation").alias("precipitation"),
        F.lit(args.bucket).alias("raw_bucket"),
        F.lit(args.object_key).alias("raw_object_key"),
        F.lit(args.event_id).alias("event_id"),
        trace_id_lit.alias("trace_id"),
        event_created_at_col.alias("event_created_at"),
        ingested_at_col.alias("ingested_at"),
    )
    raw_out.write.mode("append").jdbc(
        url=clickhouse_jdbc_url(), table=table_config["raw_table"], properties=clickhouse_props
    )

    # ODS: типизированный дневной срез (semantics: pipeline/02_ods_daily_tttr.sql).
    ods_out = (
        raw_out.select(
            F.col("wmo_index"),
            F.col("station_name"),
            F.col("country"),
            F.col("observation_date"),
            F.col("avg_temp").alias("temperature"),
            F.col("min_temp").alias("temp_min"),
            F.col("max_temp").alias("temp_max"),
            F.col("precipitation").alias("precipitation_mm"),
        )
        .withColumn("trace_id", trace_id_lit)
        .withColumn("ingested_at", ingested_at_col)
    )
    ods_out.write.mode("append").jdbc(
        url=clickhouse_jdbc_url(), table=table_config["ods_table"], properties=clickhouse_props
    )

    # DM: витрина (semantics: pipeline/03_dm_fct_daily_weather.sql — там
    # DELETE+INSERT за business_date; здесь идемпотентность повторного
    # прогона обеспечивает ReplacingMergeTree(ingested_at), см. schema.sql).
    dm_out = ods_out.select(
        F.col("wmo_index"),
        F.col("observation_date").alias("day"),
        F.col("temperature"),
        F.col("temp_min"),
        F.col("temp_max"),
        F.col("precipitation_mm"),
        F.col("trace_id"),
        F.col("ingested_at"),
    )
    dm_out.write.mode("append").jdbc(
        url=clickhouse_jdbc_url(), table=table_config["dm_table"], properties=clickhouse_props
    )

    recompute_forecast_error(
        spark, business_date=args.business_date, clickhouse_props=clickhouse_props
    )

    os.makedirs(os.path.dirname(args.result_path), exist_ok=True)
    with open(args.result_path, "w") as fh:
        json.dump(
            {
                "record_count": record_count,
                "business_date": args.business_date,
                "dataset_type": args.dataset_type,
            },
            fh,
        )

    spark.stop()


if __name__ == "__main__":
    main()
