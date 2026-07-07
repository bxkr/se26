"""PySpark job: PostgreSQL(weather_actual) -> ClickHouse (RAW/ODS/DM).

Реализует семантику infra/clickhouse/pipeline/{01,02,03}*.sql (эталон
RAW->ODS->DM из лабы sem8, Postgres-диалект, читает несуществующие
stations/weather_data) поверх реальной схемы infra/clickhouse/schema.sql,
источник данных — PostgreSQL-таблица weather_actual, которую пишет
etl_service. Подробности: data/pipeline_flow.md, "Принятые решения", п.3.

Запускается Airflow DAG'ом dm_pipeline_dag.py через spark-submit
--master local[*] (без отдельного Spark-кластера, lean-профиль).
"""

from __future__ import annotations

import argparse
import json
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--business-date", required=True, help="YYYY-MM-DD, weather_actual.observation_date")
    parser.add_argument("--trace-id", required=True)
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


def main() -> None:
    args = parse_args()

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
        table="weather_actual",
        properties=postgres_props,
    ).filter(F.col("observation_date") == args.business_date)

    record_count = raw_df.count()

    ingested_at_col = F.current_timestamp()
    trace_id_lit = F.lit(args.trace_id)

    # RAW: аудит-зеркало исходных строк weather_actual для этого business_date.
    raw_out = raw_df.withColumn("ingested_at", ingested_at_col)
    raw_out.write.mode("append").jdbc(
        url=clickhouse_jdbc_url(), table="raw_weather_events", properties=clickhouse_props
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
        url=clickhouse_jdbc_url(), table="ods_daily_weather", properties=clickhouse_props
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
        url=clickhouse_jdbc_url(), table="dm_fct_daily_weather", properties=clickhouse_props
    )

    os.makedirs(os.path.dirname(args.result_path), exist_ok=True)
    with open(args.result_path, "w") as fh:
        json.dump({"record_count": record_count, "business_date": args.business_date}, fh)

    spark.stop()


if __name__ == "__main__":
    main()
