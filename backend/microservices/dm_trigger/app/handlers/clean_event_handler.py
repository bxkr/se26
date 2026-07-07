from __future__ import annotations

import json
import uuid
from typing import Any

from app.clients.airflow_client import AirflowClient, AirflowTriggerError
from app.clients.kafka_client import KafkaProducerClient, utc_now_iso


PIPELINE_FAILED_TOPIC = "weather.pipeline.failed"


class CleanEventHandler:
    def __init__(
        self,
        *,
        airflow_client: AirflowClient,
        producer: KafkaProducerClient,
        logger: Any | None = None,
    ) -> None:
        self._airflow_client = airflow_client
        self._producer = producer
        self._logger = logger

    def handle_message(self, payload: dict[str, Any] | str | bytes) -> None:
        event = self._parse_payload(payload)
        event_id = event.get("event_id", "")
        trace_id = event.get("trace_id", "")
        business_date = event.get("observation_date")
        dataset_type = event.get("dataset_type", "actual")

        try:
            if not trace_id or not business_date:
                raise ValueError(
                    f"weather.clean.created missing trace_id/observation_date: {event}"
                )

            self._airflow_client.trigger_dag_run(
                event_id=event_id or str(uuid.uuid4()),
                trace_id=trace_id,
                business_date=business_date,
                dataset_type=dataset_type,
            )
        except (AirflowTriggerError, ValueError) as exc:
            self._log_error(
                "failed to trigger dm_pipeline DAG",
                event_id=event_id,
                trace_id=trace_id,
                error=str(exc),
            )
            self._publish_failure(trace_id=trace_id, reason="dm_trigger_failed", details=str(exc))

    def _publish_failure(self, *, trace_id: str, reason: str, details: str) -> None:
        failure_event = {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "event_type": "weather.pipeline.failed",
            "stage": "dm_trigger",
            "source_name": "dm_trigger",
            "reason": reason,
            "details": details,
            "schema_version": 1,
            "created_at": utc_now_iso(),
        }
        self._producer.send(PIPELINE_FAILED_TOPIC, failure_event)

    def _parse_payload(self, payload: dict[str, Any] | str | bytes) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, bytes):
            return json.loads(payload.decode("utf-8"))
        if isinstance(payload, str):
            return json.loads(payload)
        raise TypeError("payload must be dict, str, or bytes")

    def _log_error(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "error"):
            self._logger.error(message, **kwargs)
