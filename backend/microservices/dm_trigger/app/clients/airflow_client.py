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
        self, *, event_id: str, trace_id: str, business_date: str, dataset_type: str = "actual"
    ) -> str:
        """Trigger a run of the dm_pipeline DAG for one (trace_id, business_date).

        dag_run_id is derived from event_id so a redelivered Kafka message
        (e.g. after a commit that didn't land) triggers Airflow's existing-run
        conflict instead of a duplicate run — the whole call is idempotent.
        dataset_type ("actual"|"forecast") tells the DAG/Spark job which
        Postgres source and ClickHouse target tables to use.
        """
        dag_run_id = f"clean-{event_id}"
        url = f"{self._base_url}/api/v1/dags/{self._dag_id}/dagRuns"
        body = {
            "dag_run_id": dag_run_id,
            "conf": {
                "trace_id": trace_id,
                "business_date": business_date,
                "dataset_type": dataset_type,
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
