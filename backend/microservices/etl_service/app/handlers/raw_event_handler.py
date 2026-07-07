from __future__ import annotations

import json
from typing import Any

from app.data.schemas import (
    DailyWeatherRawDocument,
    NormalizedWeatherRecord,
    WeatherActualRawCreatedEvent,
)
from app.services.normalizer import normalize_daily_weather_raw
from app.services.validator import validate_raw_document, validate_raw_event
from app.services.writer import WeatherActualWriter


class RawEventHandler:
    def __init__(
        self,
        *,
        s3_client: Any,
        writer: WeatherActualWriter,
        logger: Any | None = None,
    ) -> None:
        self._s3_client = s3_client
        self._writer = writer
        self._logger = logger

    def handle(self, payload: dict[str, Any] | str | bytes) -> list[NormalizedWeatherRecord]:
        event_payload = self._parse_payload(payload)
        event = WeatherActualRawCreatedEvent.from_dict(event_payload)

        validate_raw_event(event)

        self._log_info(
            "raw weather event accepted",
            event_id=event.event_id,
            trace_id=event.trace_id,
            bucket=event.bucket,
            object_keys_count=len(event.object_keys),
            date_from=event.date_from,
            date_to=event.date_to,
        )

        all_records: list[NormalizedWeatherRecord] = []

        for object_key in event.object_keys:
            self._log_info(
                "loading daily raw file from s3",
                event_id=event.event_id,
                trace_id=event.trace_id,
                bucket=event.bucket,
                object_key=object_key,
            )

            raw_payload = self._read_json_from_s3(bucket=event.bucket, key=object_key)
            raw_doc = DailyWeatherRawDocument.from_dict(raw_payload)

            validate_raw_document(raw_doc, object_key)

            records = normalize_daily_weather_raw(
                event=event,
                raw_doc=raw_doc,
                object_key=object_key,
            )

            all_records.extend(records)

            self._log_info(
                "daily raw file normalized",
                event_id=event.event_id,
                trace_id=event.trace_id,
                object_key=object_key,
                records_count=len(records),
            )

        self._writer.write(all_records)

        self._log_info(
            "raw weather event processed successfully",
            event_id=event.event_id,
            trace_id=event.trace_id,
            total_records=len(all_records),
            object_keys_count=len(event.object_keys),
        )

        return all_records

    def handle_message(self, payload: dict[str, Any] | str | bytes) -> list[NormalizedWeatherRecord]:
        return self.handle(payload)

    def _parse_payload(self, payload: dict[str, Any] | str | bytes) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload

        if isinstance(payload, bytes):
            return json.loads(payload.decode("utf-8"))

        if isinstance(payload, str):
            return json.loads(payload)

        raise TypeError("payload must be dict, str, or bytes")

    def _read_json_from_s3(self, *, bucket: str, key: str) -> dict[str, Any]:
        if hasattr(self._s3_client, "get_json"):
            return self._s3_client.get_json(bucket=bucket, key=key)

        if hasattr(self._s3_client, "read_json"):
            return self._s3_client.read_json(bucket=bucket, key=key)

        if hasattr(self._s3_client, "download_json"):
            return self._s3_client.download_json(bucket=bucket, key=key)

        if hasattr(self._s3_client, "get_object"):
            try:
                raw_response = self._s3_client.get_object(bucket=bucket, key=key)
            except TypeError:
                raw_response = self._s3_client.get_object(Bucket=bucket, Key=key)

            return self._decode_s3_response(raw_response)

        raise AttributeError(
            "s3_client must expose one of: "
            "'get_json', 'read_json', 'download_json', or 'get_object'"
        )

    def _decode_s3_response(self, raw_response: Any) -> dict[str, Any]:
        if isinstance(raw_response, dict):
            if "Body" in raw_response:
                body = raw_response["Body"].read()
                return json.loads(body.decode("utf-8"))
            return raw_response

        if isinstance(raw_response, bytes):
            return json.loads(raw_response.decode("utf-8"))

        if isinstance(raw_response, str):
            return json.loads(raw_response)

        raise TypeError("unsupported s3 response type")

    def _log_info(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "info"):
            self._logger.info(message, **kwargs)