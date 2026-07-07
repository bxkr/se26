"""PySpark job: PostgreSQL(weather_actual|weather_forecast) -> ClickHouse (RAW/ODS/DM).

Реализует семантику infra/clickhouse/pipeline/{01,02,03}*.sql (эталон
RAW->ODS->DM из лабы sem8, Postgres-диалект, читает несуществующие
stations/weather_data) поверх реальной схемы infra/clickhouse/schema.sql.
--dataset-type выбирает источник и целевые таблицы: "actual" читает
weather_actual (пишет etl_service) и пишет в *_weather* таблицы, "forecast"
читает weather_forecast (временный stand-in под predict_fetcher, см.
infra/postgres/init.sql) и пишет в *_forecast* таблицы. Подробности:
data/pipeline_flow.md, "Принятые решения", п.3 и п.5.

После записи DM-слоя (в обеих ветках) пересчитывается витрина
dm_fct_forecast_error — inner join dm_fct_daily_weather x dm_fct_daily_forecast
по (wmo_index, day) для этого business_date, знаковая и абсолютная ошибка на
каждую метрику. Если второй стороны ещё нет — join пуст, ничего не пишется;
витрина дозаполнится, когда придёт вторая сторона (порядок actual/forecast
не важен).

Запускается Airflow DAG'ом dm_pipeline_dag.py через spark-submit
--master local[*] (без отдельного Spark-кластера, lean-профиль).
"""

from __future__ import annotations

import argparse
import json
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

TABLE_CONFIG = {
    "actual": {
        "source_table": "weather_actual",
        "raw_table": "raw_weather_events",
        "ods_table": "ods_daily_weather",
        "dm_table": "dm_fct_daily_weather",
    },
    "forecast": {
        "source_table": "weather_forecast",
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
    parser.add_argument("--result-path", required=True, help="where to write {record_count, business_date} JSON")
    return parser.parse_args()


def postgres_jdbc_url() -> str:
    host = os.environ["POSTGRES_HOST"]
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return f"jdbc:postgresql://{host}:{port}/{db}"


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
        .master("local[*]")
        .getOrCreate()
    )

    postgres_props = {
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "driver": "org.postgresql.Driver",
    }
    clickhouse_props = {
        "user": os.environ.get("CLICKHOUSE_USER", "default"),
        "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
        "driver": "com.clickhouse.jdbc.ClickHouseDriver",
    }

    raw_df = spark.read.jdbc(
        url=postgres_jdbc_url(),
        table=table_config["source_table"],
        properties=postgres_props,
    ).filter(F.col("observation_date") == args.business_date)

    record_count = raw_df.count()

    ingested_at_col = F.current_timestamp()
    trace_id_lit = F.lit(args.trace_id)

    # RAW: аудит-зеркало исходных строк для этого business_date.
    raw_out = raw_df.withColumn("ingested_at", ingested_at_col)
    raw_out.write.mode("append").jdbc(
        url=clickhouse_jdbc_url(), table=table_config["raw_table"], properties=clickhouse_props
    )

    # ODS: типизированный дневной срез (semantics: pipeline/02_ods_daily_tttr.sql).
    ods_out = (
        raw_df.select(
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
