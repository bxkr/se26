from __future__ import annotations

import re
from datetime import date, datetime

from app.data.schemas import DailyWeatherRawDocument, WeatherActualRawCreatedEvent


DAILY_OBJECT_KEY_RE = re.compile(r"^actual/date=(\d{4}-\d{2}-\d{2})\.json$")


class ValidationError(ValueError):
    pass


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO date: {value}") from exc


def parse_iso_datetime(value: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO datetime: {value}") from exc


def extract_date_from_object_key(object_key: str) -> str:
    match = DAILY_OBJECT_KEY_RE.match(object_key)
    if not match:
        raise ValidationError(
            f"Invalid object key format: {object_key}. "
            f"Expected format: actual/date=YYYY-MM-DD.json"
        )
    return match.group(1)


def validate_raw_event(event: WeatherActualRawCreatedEvent) -> None:
    if not event.event_id:
        raise ValidationError("event_id is required")

    if not event.trace_id:
        raise ValidationError("trace_id is required")

    if event.event_type != "weather.actual.raw.created":
        raise ValidationError(
            f"Unexpected event_type: {event.event_type}. "
            f"Expected: weather.actual.raw.created"
        )

    if not event.source_name:
        raise ValidationError("source_name is required")

    if not event.bucket:
        raise ValidationError("bucket is required")

    if not isinstance(event.object_keys, list) or not event.object_keys:
        raise ValidationError("object_keys must be a non-empty list")

    date_from = parse_iso_date(event.date_from)
    date_to = parse_iso_date(event.date_to)

    if date_from > date_to:
        raise ValidationError("date_from must be less than or equal to date_to")

    parse_iso_datetime(event.created_at)

    seen_keys: set[str] = set()

    for object_key in event.object_keys:
        if not object_key:
            raise ValidationError("object_keys must not contain empty values")

        if object_key in seen_keys:
            raise ValidationError(f"Duplicate object key detected: {object_key}")
        seen_keys.add(object_key)

        key_date_str = extract_date_from_object_key(object_key)
        key_date = parse_iso_date(key_date_str)

        if key_date < date_from or key_date > date_to:
            raise ValidationError(
                f"Object key date {key_date_str} is outside range "
                f"{event.date_from}..{event.date_to}"
            )


def validate_raw_document(raw_doc: DailyWeatherRawDocument, object_key: str) -> None:
    if not raw_doc.date:
        raise ValidationError("raw document field 'date' is required")

    parse_iso_date(raw_doc.date)

    key_date = extract_date_from_object_key(object_key)

    if raw_doc.date != key_date:
        raise ValidationError(
            f"raw document date '{raw_doc.date}' does not match key date '{key_date}'"
        )

    if raw_doc.stations is None:
        raise ValidationError("raw document field 'stations' is required")

    if not isinstance(raw_doc.stations, list):
        raise ValidationError("'stations' must be a list")

    for index, station in enumerate(raw_doc.stations):
        if not station.wmo_index:
            raise ValidationError(f"stations[{index}].wmo_index is required")

        if not station.name:
            raise ValidationError(f"stations[{index}].name is required")

        if not station.country:
            raise ValidationError(f"stations[{index}].country is required")