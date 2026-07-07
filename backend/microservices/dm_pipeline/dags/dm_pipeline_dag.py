"""DAG: PostgreSQL(weather_actual) -> ClickHouse (RAW/ODS/DM), одна из
двух половин dm_trigger -> Airflow -> Spark -> ClickHouse, описанной в
data/pipeline_flow.md.

Триггерится ТОЛЬКО извне (dm_trigger, POST /api/v1/dags/dm_pipeline/dagRuns
с conf={trace_id, business_date}) — расписания нет.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

sys.path.insert(0, str(Path(__file__).parent))
from common.kafka_events import publish_event  # noqa: E402

DAG_ID = "dm_pipeline"
SPARK_JOB_PATH = "/opt/spark_jobs/postgres_to_clickhouse.py"
RESULT_DIR = "/opt/airflow/spark_results"
SPARK_JARS = "/opt/spark_jars/postgresql.jar,/opt/spark_jars/clickhouse-jdbc.jar"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _result_path(trace_id: str) -> str:
    return f"{RESULT_DIR}/{trace_id}.json"


def publish_dm_ready(**context) -> None:
    import json

    conf = context["dag_run"].conf or {}
    trace_id = conf["trace_id"]
    business_date = conf["business_date"]
    dataset_type = conf.get("dataset_type", "actual")

    with open(_result_path(trace_id)) as fh:
        result = json.load(fh)

    event = {
        "event_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "event_type": "weather.dm.ready",
        "dataset_type": dataset_type,
        "observation_date": business_date,
        "record_count": result["record_count"],
        "schema_version": 1,
        "created_at": _utc_now_iso(),
    }
    publish_event("weather.dm.ready", event)


def publish_pipeline_failed(context) -> None:
    dag_run = context.get("dag_run")
    conf = (dag_run.conf if dag_run else {}) or {}
    exception = context.get("exception")

    event = {
        "event_id": str(uuid.uuid4()),
        "trace_id": conf.get("trace_id", ""),
        "event_type": "weather.pipeline.failed",
        "stage": "dm",
        "source_name": "dm_pipeline",
        "reason": "dag_task_failed",
        "details": str(exception)[:1000] if exception else f"{DAG_ID} DAG failed",
        "schema_version": 1,
        "created_at": _utc_now_iso(),
    }
    publish_event("weather.pipeline.failed", event)


with DAG(
    dag_id=DAG_ID,
    description="weather_actual (PostgreSQL) -> ClickHouse RAW/ODS/DM via PySpark, triggered per weather.clean.created",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=8,
    tags=["dm", "spark", "clickhouse"],
    on_failure_callback=publish_pipeline_failed,
) as dag:
    run_spark_transform = BashOperator(
        task_id="run_spark_transform",
        bash_command=(
            f"mkdir -p {RESULT_DIR} && "
            # local[2] + explicit driver-memory: data volume here is one
            # business_date (hundreds of rows, not big data) — local[*] plus
            # Spark's own heap sizing on top of the concurrently-running
            # Airflow webserver/scheduler/triggerer OOMKilled the pod on the
            # first real run.
            f"spark-submit --master local[2] --driver-memory 1g --jars {SPARK_JARS} {SPARK_JOB_PATH} "
            "--business-date {{ dag_run.conf['business_date'] }} "
            "--trace-id {{ dag_run.conf['trace_id'] }} "
            "--dataset-type {{ dag_run.conf.get('dataset_type', 'actual') }} "
            f"--result-path {RESULT_DIR}/"
            "{{ dag_run.conf['trace_id'] }}.json"
        ),
    )

    publish_dm_ready_task = PythonOperator(
        task_id="publish_dm_ready",
        python_callable=publish_dm_ready,
    )

    run_spark_transform >> publish_dm_ready_task
