from __future__ import annotations

import json
import uuid
from typing import Any

from app.clients.airflow_client import AirflowClient, AirflowTriggerError
from app.clients.kafka_client import KafkaProducerClient, utc_now_iso


PIPELINE_FAILED_TOPIC = "weather.pipeline.failed"

TOPIC_TO_DATASET_TYPE = {
    "weather.actual.raw.created": "actual",
    "weather.forecast.raw.created": "forecast",
}


class RawCreatedEventHandler:
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

    def handle_message(self, payload: dict[str, Any] | str | bytes, topic: str) -> None:
        event = self._parse_payload(payload)
        event_id = event.get("event_id") or str(uuid.uuid4())
        trace_id = event.get("trace_id", "")
        bucket = event.get("bucket")
        object_keys = event.get("object_keys") or []
        date_from = event.get("date_from")
        date_to = event.get("date_to")
        source_name = event.get("source_name", "")
        event_created_at = event.get("created_at", "")
        dataset_type = TOPIC_TO_DATASET_TYPE.get(topic, "actual")

        if not trace_id or not bucket or not object_keys or not date_from or not date_to:
            self._log_error(
                "raw.created event missing trace_id/bucket/object_keys/date_from/date_to",
                event_id=event_id,
                topic=topic,
                event=event,
            )
            self._publish_failure(
                trace_id=trace_id,
                reason="dm_trigger_invalid_event",
                details=f"missing trace_id/bucket/object_keys/date_from/date_to in {topic} event",
            )
            return

        # The manifest already spans the whole date_from..date_to range in
        # one event — a single DAG run now processes the whole range in one
        # Spark job (s3_to_clickhouse.py reads all of object_keys via one
        # S3A multi-file read), instead of fanning out one DAG run per day.
        try:
            self._airflow_client.trigger_dag_run(
                event_id=event_id,
                trace_id=trace_id,
                date_from=date_from,
                date_to=date_to,
                dataset_type=dataset_type,
                bucket=bucket,
                source_name=source_name,
                event_created_at=event_created_at,
            )
        except AirflowTriggerError as exc:
            self._log_error(
                "failed to trigger dm_pipeline DAG",
                event_id=event_id,
                trace_id=trace_id,
                date_from=date_from,
                date_to=date_to,
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
