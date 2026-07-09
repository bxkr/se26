"""PySpark job: S3 raw daily JSON (whole date_from..date_to range) -> ClickHouse (RAW/ODS/DM).

Reads every daily raw file in [date_from, date_to] for one dataset_type
(`s3a://<bucket>/<prefix>/date=<day>.json`, one JSON document per day
`{date, stations: [...]}`) directly via the S3A connector in a single
multi-file read — no Postgres involved anymore (see data/pipeline_flow.md,
"Принятые решения"). One Spark job now processes the whole range in one
JVM instead of one job per day (see dm_trigger's RawCreatedEventHandler and
dm_pipeline_dag.py) — a day-by-day fan-out used to mean one spark-submit
JVM per day, which was the actual bottleneck for wide date ranges, not data
volume (even a month of daily files is a few hundred rows).
--dataset-type selects the target ClickHouse tables and the S3 key prefix:
"actual" writes *_weather* tables (source: historical_fetcher via
weather.actual.raw.created), "forecast" writes *_forecast* tables (source:
forecast_fetcher via weather.forecast.raw.created).

After writing the DM layer (in either branch) the dm_fct_forecast_error mart
is recomputed — inner join dm_fct_daily_weather x dm_fct_daily_forecast on
(wmo_index, day) for every day in [date_from, date_to], signed and absolute
error per metric. Days where the other side doesn't exist yet are simply
absent from the join; the mart backfills whenever the second side arrives
(order of actual/forecast doesn't matter).

Run by dm_pipeline_dag.py as a thin Spark Connect client against the
persistent server in backend/deploy/helm/spark-connect (see
build_spark_session) — falls back to a local[2] driver when no Connect
server is configured (docker-compose / local dev).
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

TABLE_CONFIG = {
    "actual": {
        "prefix": "actual",
        "raw_table": "raw_weather_events",
        "ods_table": "ods_daily_weather",
        "dm_table": "dm_fct_daily_weather",
    },
    "forecast": {
        "prefix": "forecast",
        "raw_table": "raw_forecast_events",
        "ods_table": "ods_daily_forecast",
        "dm_table": "dm_fct_daily_forecast",
    },
}

ERROR_METRICS = ["temperature", "temp_min", "temp_max", "precipitation_mm"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-from", required=True, help="YYYY-MM-DD, inclusive range start")
    parser.add_argument("--date-to", required=True, help="YYYY-MM-DD, inclusive range end")
    parser.add_argument("--trace-id", required=True)
    parser.add_argument(
        "--dataset-type", required=True, choices=sorted(TABLE_CONFIG), help="actual|forecast"
    )
    parser.add_argument("--bucket", required=True, help="S3 bucket holding the raw daily JSON files")
    parser.add_argument("--source-name", required=True, help="producer of the raw files, e.g. historical_fetcher")
    parser.add_argument("--event-id", required=True, help="raw.created event_id (unique per manifest)")
    parser.add_argument("--event-created-at", required=True, help="ISO8601 created_at from the raw.created event")
    parser.add_argument("--result-path", required=True, help="where to write {record_count, date_from, date_to} JSON")
    parser.add_argument(
        "--spark-connect-url",
        default=os.environ.get("SPARK_CONNECT_URL"),
        help="sc://host:port of a persistent Spark Connect server. When set, this process is a thin "
        "gRPC client (no local JVM/S3A/driver startup) instead of spawning its own local[2] Spark "
        "driver — S3A and ClickHouse-JDBC configuration then live server-side, not here. Falls back "
        "to a local driver when unset (docker-compose / no Connect server deployed).",
    )
    return parser.parse_args()


def build_spark_session(*, app_name: str, spark_connect_url: str | None) -> SparkSession:
    if spark_connect_url:
        return SparkSession.builder.appName(app_name).remote(spark_connect_url).getOrCreate()
    return (
        SparkSession.builder.appName(app_name)
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


def _daterange(date_from: str, date_to: str) -> list[str]:
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _object_keys_for_range(dataset_type: str, date_from: str, date_to: str) -> list[str]:
    # historical_fetcher/ForecastFetcher always write exactly one file per
    # day in the requested range before publishing the manifest receipt
    # (even when the upstream source has no data for that day — the file
    # still exists with null measurement fields) — so the object key for
    # every day is fully deterministic, no need to carry the manifest's
    # object_keys list through to Spark.
    prefix = TABLE_CONFIG[dataset_type]["prefix"]
    return [f"{prefix}/date={day}.json" for day in _daterange(date_from, date_to)]


def clickhouse_jdbc_url() -> str:
    host = os.environ["CLICKHOUSE_HOST"]
    port = os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")
    db = os.environ.get("CLICKHOUSE_DB", "weather")
    return f"jdbc:clickhouse://{host}:{port}/{db}"


def recompute_forecast_error(
    spark: SparkSession, *, date_from: str, date_to: str, clickhouse_props: dict
) -> None:
    """Recompute dm_fct_forecast_error for every day in [date_from, date_to]
    from the current DM tables (both actual and forecast may or may not be
    populated yet for any given day)."""
    weather_df = spark.read.jdbc(
        url=clickhouse_jdbc_url(),
        table="dm_fct_daily_weather_current",
        properties=clickhouse_props,
    ).filter(F.col("day").between(F.lit(date_from), F.lit(date_to)))
    forecast_df = spark.read.jdbc(
        url=clickhouse_jdbc_url(),
        table="dm_fct_daily_forecast_current",
        properties=clickhouse_props,
    ).filter(F.col("day").between(F.lit(date_from), F.lit(date_to)))

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

    spark = build_spark_session(
        app_name=f"dm_pipeline-{args.trace_id}", spark_connect_url=args.spark_connect_url
    )
    stations_df = None
    try:
        stations_df = _run(spark, args, table_config)
    finally:
        if stations_df is not None:
            stations_df.unpersist()
        spark.stop()


def _run(spark: SparkSession, args: argparse.Namespace, table_config: dict):
    """Returns the cached stations_df so the caller can unpersist it — kept
    as one function (not split further) since every downstream DataFrame
    here is derived from it and the flow reads top-to-bottom as one script."""
    clickhouse_props = {
        "user": os.environ.get("CLICKHOUSE_USER", "default"),
        "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
        "driver": "com.clickhouse.jdbc.ClickHouseDriver",
    }

    object_keys = _object_keys_for_range(args.dataset_type, args.date_from, args.date_to)
    paths = [f"s3a://{args.bucket}/{key}" for key in object_keys]

    # Each raw file is a single JSON document {date, stations: [...]}, not
    # JSON-lines — multiLine is required or Spark reads it as truncated
    # junk. Spark natively accepts a list of paths and unions them into one
    # DataFrame — this is what turns N per-day JVMs into one JVM for the
    # whole range.
    raw_doc_df = spark.read.option("multiLine", "true").json(paths).withColumn(
        # Recovers which source file each row came from, since object_key
        # is no longer a single literal shared by every row in the batch —
        # captured right at read time (before explode) and carried through,
        # stripping the s3a://bucket/ prefix down to "<prefix>/date=....json".
        "raw_object_key",
        F.regexp_extract(F.input_file_name(), r"([^/]+/date=[0-9-]+\.json)$", 1),
    )
    stations_df = raw_doc_df.select(
        F.col("date").alias("observation_date"),
        F.explode("stations").alias("station"),
        F.col("raw_object_key"),
    )
    # Without this, every action below (count, then the 3 separate .write.jdbc
    # calls for raw/ods/dm) re-executes this whole lineage from scratch —
    # re-reading and re-parsing every S3 file once per action instead of
    # once total. Cheap to keep in memory (a date range here is at most a
    # few hundred rows) and matters more now that a persistent Spark Connect
    # server (see build_spark_session) runs many requests' data through the
    # same long-lived driver — unpersisted here at the end either way so it
    # doesn't accumulate across requests.
    stations_df.cache()

    # int(): under Spark Connect, .count() returns numpy.int64 (Arrow-backed
    # result collection), not a plain Python int like classic local Spark —
    # json.dump rejects numpy.int64 with "Object of type int64 is not JSON
    # serializable" further down otherwise.
    record_count = int(stations_df.count())

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

    # RAW: аудит-зеркало исходных station-строк за весь диапазон дат.
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
        F.col("raw_object_key"),
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
        spark, date_from=args.date_from, date_to=args.date_to, clickhouse_props=clickhouse_props
    )

    os.makedirs(os.path.dirname(args.result_path), exist_ok=True)
    with open(args.result_path, "w") as fh:
        json.dump(
            {
                "record_count": record_count,
                "date_from": args.date_from,
                "date_to": args.date_to,
                "dataset_type": args.dataset_type,
            },
            fh,
        )

    return stations_df


if __name__ == "__main__":
    main()
