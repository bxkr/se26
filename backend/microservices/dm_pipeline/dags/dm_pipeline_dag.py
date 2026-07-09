"""DAG: S3 (raw JSON за диапазон дат) -> ClickHouse (RAW/ODS/DM), одна из
двух половин dm_trigger -> Airflow -> Spark -> ClickHouse, описанной в
data/pipeline_flow.md.

Триггерится ТОЛЬКО извне (dm_trigger, POST /api/v1/dags/dm_pipeline/dagRuns
с conf={trace_id, date_from, date_to, dataset_type, bucket, source_name,
event_id, event_created_at}) — расписания нет. Один DAG-ран обрабатывает
весь диапазон date_from..date_to одним Spark-джобом (см.
spark_jobs/s3_to_clickhouse.py) — не по одному рану на день.
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
SPARK_JOB_PATH = "/opt/spark_jobs/s3_to_clickhouse.py"
RESULT_DIR = "/opt/airflow/spark_results"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _result_path(run_id: str) -> str:
    # dag_run_id is unique per manifest event now (one DAG run per manifest,
    # not per day) — still keyed by dag_run.run_id rather than event_id/
    # trace_id alone, since a redelivered Kafka message reuses the same
    # dag_run_id and should overwrite the same result file, not collide.
    return f"{RESULT_DIR}/{run_id}.json"


def publish_dm_ready(**context) -> None:
    import json

    dag_run = context["dag_run"]
    conf = dag_run.conf or {}
    trace_id = conf["trace_id"]
    date_from = conf["date_from"]
    date_to = conf["date_to"]
    dataset_type = conf.get("dataset_type", "actual")

    with open(_result_path(dag_run.run_id)) as fh:
        result = json.load(fh)

    event = {
        "event_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "event_type": "weather.dm.ready",
        "dataset_type": dataset_type,
        "date_from": date_from,
        "date_to": date_to,
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
    description="S3 raw daily JSON -> ClickHouse RAW/ODS/DM via PySpark, triggered per weather.{actual,forecast}.raw.created",
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
            # Plain python3, not spark-submit: SPARK_CONNECT_URL (set on
            # this pod's env, see backend/deploy/helm/airflow) makes
            # s3_to_clickhouse.py a thin gRPC client against the persistent
            # Spark Connect server (backend/deploy/helm/spark-connect) — no
            # local JVM/driver spins up here anymore, so no --master/--jars/
            # --driver-memory. Falls back to a local[2] driver in this same
            # process if SPARK_CONNECT_URL is unset (docker-compose / local
            # dev without a Connect server deployed).
            f"python3 {SPARK_JOB_PATH} "
            "--date-from {{ dag_run.conf['date_from'] }} "
            "--date-to {{ dag_run.conf['date_to'] }} "
            "--trace-id {{ dag_run.conf['trace_id'] }} "
            "--dataset-type {{ dag_run.conf['dataset_type'] }} "
            "--bucket {{ dag_run.conf['bucket'] }} "
            "--source-name {{ dag_run.conf['source_name'] }} "
            "--event-id {{ dag_run.conf['event_id'] }} "
            "--event-created-at {{ dag_run.conf['event_created_at'] }} "
            f"--result-path {RESULT_DIR}/"
            "{{ dag_run.run_id }}.json"
        ),
    )

    publish_dm_ready_task = PythonOperator(
        task_id="publish_dm_ready",
        python_callable=publish_dm_ready,
    )

    run_spark_transform >> publish_dm_ready_task
