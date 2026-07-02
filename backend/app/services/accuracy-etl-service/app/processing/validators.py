from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models.raw_events import ActualRawEvent, ForecastRawEvent


SUPPORTED_METRICS = {
    "temperature",
    "wind_speed",
    "humidity",
    "pressure",
    "precipitation",
}

SUPPORTED_UNITS_BY_METRIC = {
    "temperature": {"C", "c", "°C", "celsius", "F", "f", "°F", "fahrenheit"},
    "wind_speed": {"m/s", "mps", "meter_per_second", "meters_per_second", "km/h", "kph", "kmh"},
    "humidity": {"%", "percent"},
    "pressure": {"hPa", "hpa", "Pa", "pa"},
    "precipitation": {"mm", "millimeter", "millimeters"},
}


VALUE_RANGES = {
    "temperature": (-100.0, 100.0),
    "wind_speed": (0.0, 150.0),
    "humidity": (0.0, 100.0),
    "pressure": (100.0, 120000.0),
    "precipitation": (0.0, 1000.0),
}

class RejectEventError(ValueError):
    """Нормальный reject для невалидных событий"""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def reject(code: str, message: str, **details) -> None:
    """reject невалидных событий"""

    raise RejectEventError(code=code, message=message, details=details)


def ensure_not_blank(value: str, field_name: str) -> None:
    """Проверяет на пустоту"""

    if not value or not value.strip():
        reject("blank_field", f"{field_name} must not be blank", field=field_name)


def ensure_supported_metric(metric_type: str) -> None:
    """Проверяет метрику на поддерживаемость"""

    metric = metric_type.strip().lower()
    if metric not in SUPPORTED_METRICS:
        reject("unsupported_metric", f"Unsupported metric_type: {metric_type}", metric_type=metric_type)


def ensure_supported_unit(metric_type: str, unit: str) -> None:
    """Проверяет единицу измерения на поддерживаемость"""

    metric = metric_type.strip().lower()
    allowed_units = SUPPORTED_UNITS_BY_METRIC.get(metric)

    if not allowed_units:
        reject("metric_unit_config_missing", f"No unit config for metric_type: {metric_type}", metric_type=metric_type)

    if unit.strip() not in allowed_units:
        reject(
            "unsupported_unit",
            f"Unsupported unit '{unit}' for metric_type '{metric_type}'",
            metric_type=metric_type,
            unit=unit,
            allowed_units=sorted(allowed_units),
        )


def ensure_value_in_range(metric_type: str, value: float) -> None:
    """Проверяет, что значение не выходит из диапазона возможных"""

    metric = metric_type.strip().lower()
    min_value, max_value = VALUE_RANGES[metric]

    if not (min_value <= value <= max_value):
        reject(
            "value_out_of_range",
            f"Value {value} is out of allowed range for metric_type '{metric_type}'",
            metric_type=metric_type,
            value=value,
            min_value=min_value,
            max_value=max_value,
        )


def ensure_timezone_valid(timezone_name: str) -> None:
    """Проверяет временную зону на валидность"""

    if not timezone_name or not timezone_name.strip():
        reject("blank_timezone", "timezone must not be blank")

    try:
        ZoneInfo(timezone_name)
        return timezone_name
    except Exception:
        reject("invalid_timezone", f"Invalid timezone: {timezone_name}", timezone=timezone_name)


def ensure_forecast_time_order(
    forecast_created_at: datetime,
    forecast_for_time: datetime,
) -> None:
    """Проверяет, что forecast_for не раньше чем forecast_created"""

    created = _ensure_datetime_aware(forecast_created_at)
    target = _ensure_datetime_aware(forecast_for_time)

    if target < created:
        reject(
            "invalid_forecast_time_order",
            "forecast_for_time must be greater than or equal to forecast_created_at",
            forecast_created_at=forecast_created_at.isoformat(),
            forecast_for_time=forecast_for_time.isoformat(),
        )


def ensure_datetime_not_too_far_in_future(
    dt: datetime,
    field_name: str,
    max_hours_ahead: int = 24,
) -> None:
    """Проверяет, что forecast_for не на слишком далекое будущее"""

    dt_utc = _ensure_datetime_aware(dt).astimezone(timezone.utc)
    now_utc = datetime.now(timezone.utc)

    delta_hours = (dt_utc - now_utc).total_seconds() / 3600
    if delta_hours > max_hours_ahead:
        reject(
            "datetime_too_far_in_future",
            f"{field_name} is too far in the future",
            field=field_name,
            datetime_value=dt.isoformat(),
            max_hours_ahead=max_hours_ahead,
            actual_hours_ahead=round(delta_hours, 4),
        )


def ensure_raw_s3_key_valid(raw_s3_key: str) -> None:
    """Проверяет, что raw_s3_key не пуст"""

    ensure_not_blank(raw_s3_key, "raw_s3_key")


def _ensure_datetime_aware(dt: datetime) -> datetime:
    """Проверяет наличие информации о временной зоне"""

    if dt.tzinfo is None:
        reject("naive_datetime", f"Datetime must be timezone-aware: {dt}", datetime_value=str(dt))
    return dt

def resolve_timezone_name(
    explicit_timezone: str | None = None,
    station_timezone: str | None = None,
    region_timezone: str | None = None,
    allow_utc_fallback: bool = False,
) -> str:
    """
    Определяет временную зону по приоритету:
    1. timezone из события
    2. timezone станции
    3. timezone региона
    4. UTC fallback, если разрешен
    """
    
    if explicit_timezone:
        return ensure_timezone_valid(explicit_timezone)

    if station_timezone:
        return ensure_timezone_valid(station_timezone)

    if region_timezone:
        return ensure_timezone_valid(region_timezone)

    if allow_utc_fallback:
        return "UTC"

    reject(
        "timezone_resolution_failed",
        "Could not resolve timezone for naive datetime",
        explicit_timezone=explicit_timezone,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )


def ensure_datetime_aware_or_resolve(
    dt: datetime,
    field_name: str,
    explicit_timezone: str | None = None,
    station_timezone: str | None = None,
    region_timezone: str | None = None,
    allow_utc_fallback: bool = False,
) -> datetime:
    """
    Если datetime уже aware — возвращаем как есть.
    Если naive — пытаемся навесить timezone по fallback strategy.
    """

    if dt.tzinfo is not None:
        return dt

    tz_name = resolve_timezone_name(
        explicit_timezone=explicit_timezone,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    try:
        return dt.replace(tzinfo=ZoneInfo(tz_name))
    except Exception:
        reject(
            "datetime_timezone_attach_failed",
            f"Failed to attach timezone to naive datetime for field {field_name}",
            field=field_name,
            datetime_value=str(dt),
            resolved_timezone=tz_name,
        )


def validate_forecast_raw(
    event: ForecastRawEvent,
    station_timezone: str | None = None,
    region_timezone: str | None = None,
    allow_utc_fallback: bool = False,
) -> ForecastRawEvent:
    """Проверяет forecast на валидность"""

    ensure_not_blank(event.source_type, "source_type")
    ensure_not_blank(event.source_name, "source_name")
    ensure_not_blank(event.schema_version, "schema_version")
    ensure_not_blank(event.station_id, "station_id")
    ensure_not_blank(event.region_id, "region_id")
    ensure_supported_metric(event.metric_type)
    ensure_supported_unit(event.metric_type, event.unit)
    ensure_value_in_range(event.metric_type, event.value)
    ensure_raw_s3_key_valid(event.raw_s3_key)

    timezone_name = resolve_timezone_name(
        explicit_timezone=event.timezone,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    ingested_at = ensure_datetime_aware_or_resolve(
        event.ingested_at,
        "ingested_at",
        explicit_timezone=timezone_name,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    forecast_created_at = ensure_datetime_aware_or_resolve(
        event.forecast_created_at,
        "forecast_created_at",
        explicit_timezone=timezone_name,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    forecast_for_time = ensure_datetime_aware_or_resolve(
        event.forecast_for_time,
        "forecast_for_time",
        explicit_timezone=timezone_name,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    ensure_forecast_time_order(forecast_created_at, forecast_for_time)
    ensure_datetime_not_too_far_in_future(ingested_at, "ingested_at")

    return event.model_copy(
        update={
            "timezone": timezone_name,
            "ingested_at": ingested_at,
            "forecast_created_at": forecast_created_at,
            "forecast_for_time": forecast_for_time,
        }
    )


def validate_actual_raw(
    event: ActualRawEvent,
    station_timezone: str | None = None,
    region_timezone: str | None = None,
    allow_utc_fallback: bool = False,
) -> ActualRawEvent:
    """Проверяет actual на валидность"""
    
    ensure_not_blank(event.source_type, "source_type")
    ensure_not_blank(event.source_name, "source_name")
    ensure_not_blank(event.schema_version, "schema_version")
    ensure_not_blank(event.station_id, "station_id")
    ensure_not_blank(event.region_id, "region_id")
    ensure_not_blank(event.sensor_id, "sensor_id")
    ensure_supported_metric(event.metric_type)
    ensure_supported_unit(event.metric_type, event.unit)
    ensure_value_in_range(event.metric_type, event.value)
    ensure_raw_s3_key_valid(event.raw_s3_key)

    ingested_at = ensure_datetime_aware_or_resolve(
        event.ingested_at,
        "ingested_at",
        explicit_timezone=None,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    measured_at = ensure_datetime_aware_or_resolve(
        event.measured_at,
        "measured_at",
        explicit_timezone=None,
        station_timezone=station_timezone,
        region_timezone=region_timezone,
        allow_utc_fallback=allow_utc_fallback,
    )

    ensure_datetime_not_too_far_in_future(ingested_at, "ingested_at")
    ensure_datetime_not_too_far_in_future(measured_at, "measured_at")

    return event.model_copy(
        update={
            "ingested_at": ingested_at,
            "measured_at": measured_at,
        }
    )