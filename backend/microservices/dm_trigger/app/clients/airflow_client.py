from __future__ import annotations

import os
from typing import Any

import requests


class AirflowTriggerError(RuntimeError):
    """Raised when Airflow rejects or fails to accept a DAG run trigger."""


class AirflowClient:
    def __init__(
        self,
        *,
        base_url: str,
        dag_id: str,
        username: str,
        password: str,
        timeout_seconds: float = 10.0,
        logger: Any | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._dag_id = dag_id
        self._auth = (username, password)
        self._timeout_seconds = timeout_seconds
        self._logger = logger

    @classmethod
    def from_env(cls, *, logger: Any | None = None) -> "AirflowClient":
        return cls(
            base_url=os.getenv("AIRFLOW_BASE_URL", "http://airflow:8080"),
            dag_id=os.getenv("AIRFLOW_DAG_ID", "dm_pipeline"),
            username=os.getenv("AIRFLOW_API_USERNAME", "admin"),
            password=os.getenv("AIRFLOW_API_PASSWORD", "admin"),
            timeout_seconds=float(os.getenv("AIRFLOW_API_TIMEOUT_SECONDS", "10")),
            logger=logger,
        )

    def trigger_dag_run(
        self,
        *,
        event_id: str,
        trace_id: str,
        business_date: str,
        dataset_type: str,
        bucket: str,
        object_key: str,
        source_name: str,
        event_created_at: str,
    ) -> str:
        """Trigger a run of the dm_pipeline DAG for one (trace_id, business_date).

        dag_run_id combines event_id with business_date so a redelivered
        Kafka message triggers Airflow's existing-run conflict instead of a
        duplicate run (idempotent), and so multiple dates fanned out from
        the same manifest event get distinct DAG runs. event_id itself is
        passed through to conf unmodified — it's written into ClickHouse's
        event_id UUID column by the Spark job, so it must stay a real UUID.
        dataset_type ("actual"|"forecast") tells the DAG/Spark job which
        ClickHouse target tables to use; bucket/object_key tell Spark which
        raw JSON file to read directly from S3.
        """
        dag_run_id = f"{dataset_type}-{event_id}-{business_date}"
        url = f"{self._base_url}/api/v1/dags/{self._dag_id}/dagRuns"
        body = {
            "dag_run_id": dag_run_id,
            "conf": {
                "trace_id": trace_id,
                "business_date": business_date,
                "dataset_type": dataset_type,
                "bucket": bucket,
                "object_key": object_key,
                "source_name": source_name,
                "event_id": event_id,
                "event_created_at": event_created_at,
            },
        }

        try:
            response = requests.post(url, json=body, auth=self._auth, timeout=self._timeout_seconds)
        except requests.RequestException as exc:
            raise AirflowTriggerError(f"airflow request failed: {exc}") from exc

        if response.status_code == 409:
            self._log_info(
                "dag run already exists, treating as success",
                dag_run_id=dag_run_id,
                trace_id=trace_id,
            )
            return dag_run_id

        if response.status_code not in (200, 201):
            raise AirflowTriggerError(
                f"airflow returned {response.status_code}: {response.text[:500]}"
            )

        self._log_info(
            "dag run triggered",
            dag_run_id=dag_run_id,
            trace_id=trace_id,
            business_date=business_date,
        )
        return dag_run_id

    def _log_info(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "info"):
            self._logger.info(message, **kwargs)
