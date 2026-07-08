from __future__ import annotations

import json
import re
import uuid
from typing import Any

from app.clients.airflow_client import AirflowClient, AirflowTriggerError
from app.clients.kafka_client import KafkaProducerClient, utc_now_iso


PIPELINE_FAILED_TOPIC = "weather.pipeline.failed"

TOPIC_TO_DATASET_TYPE = {
    "weather.actual.raw.created": "actual",
    "weather.forecast.raw.created": "forecast",
}

# Matches both "actual/date=YYYY-MM-DD.json" and "forecast/date=YYYY-MM-DD.json".
OBJECT_KEY_DATE_RE = re.compile(r"date=(\d{4}-\d{2}-\d{2})\.json$")


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
        event_id = event.get("event_id", "")
        trace_id = event.get("trace_id", "")
        bucket = event.get("bucket")
        object_keys = event.get("object_keys") or []
        source_name = event.get("source_name", "")
        event_created_at = event.get("created_at", "")
        dataset_type = TOPIC_TO_DATASET_TYPE.get(topic, "actual")

        if not trace_id or not bucket or not object_keys:
            self._log_error(
                "raw.created event missing trace_id/bucket/object_keys",
                event_id=event_id,
                topic=topic,
                event=event,
            )
            self._publish_failure(
                trace_id=trace_id,
                reason="dm_trigger_invalid_event",
                details=f"missing trace_id/bucket/object_keys in {topic} event",
            )
            return

        # One manifest event can span several dates (date_from..date_to); a
        # DAG run only handles one business_date, so fan out into one
        # trigger per object_key. A failure on one date must not stop the
        # rest of the batch from being processed.
        for object_key in object_keys:
            self._trigger_for_object_key(
                event_id=event_id or str(uuid.uuid4()),
                trace_id=trace_id,
                bucket=bucket,
                object_key=object_key,
                source_name=source_name,
                event_created_at=event_created_at,
                dataset_type=dataset_type,
            )

    def _trigger_for_object_key(
        self,
        *,
        event_id: str,
        trace_id: str,
        bucket: str,
        object_key: str,
        source_name: str,
        event_created_at: str,
        dataset_type: str,
    ) -> None:
        match = OBJECT_KEY_DATE_RE.search(object_key)

        try:
            if not match:
                raise ValueError(f"object_key does not contain a parseable date: {object_key}")

            business_date = match.group(1)

            # event_id stays the real manifest UUID — it's written into
            # ClickHouse's event_id UUID column by the Spark job, so it must
            # not be mangled. Per-date uniqueness (for dag_run_id) is the
            # airflow_client's job, combining event_id with business_date.
            self._airflow_client.trigger_dag_run(
                event_id=event_id,
                trace_id=trace_id,
                business_date=business_date,
                dataset_type=dataset_type,
                bucket=bucket,
                object_key=object_key,
                source_name=source_name,
                event_created_at=event_created_at,
            )
        except (AirflowTriggerError, ValueError) as exc:
            self._log_error(
                "failed to trigger dm_pipeline DAG",
                event_id=event_id,
                trace_id=trace_id,
                object_key=object_key,
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
