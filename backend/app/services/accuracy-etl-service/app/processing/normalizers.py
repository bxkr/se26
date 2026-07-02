from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models.normalized_events import (
    NormalizedActualRecord,
    NormalizedForecastRecord,
)
from app.models.raw_events import (
    ActualRawEvent,
    ForecastRawEvent,
)


METRIC_TYPE_ALIASES = {
    "temp": "temperature",
    "temperature": "temperature",
    "wind": "wind_speed",
    "wind_speed": "wind_speed",
    "humidity": "humidity",
    "pressure": "pressure",
    "precipitation": "precipitation",
}


def normalize_metric_type(metric_type: str) -> str:
    """Нормализует тип метрики"""

    value = metric_type.strip().lower()
    return METRIC_TYPE_ALIASES.get(value, value)


def to_utc(dt: datetime, tz_name: str | None = None) -> datetime:
    """Переводит в utc"""

    if dt.tzinfo is None:
        if tz_name:
            dt = dt.replace(tzinfo=ZoneInfo(tz_name))
        else:
            dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_timezone_name(tz_name: str | None) -> str:
    """Нормализует имя временной зоны"""

    if not tz_name:
        return "UTC"

    try:
        ZoneInfo(tz_name)
        return tz_name
    except Exception:
        return "UTC"


def convert_temperature_to_celsius(value: float, unit: str) -> tuple[float, str]:
    """Конвертирует температуру в цельсии"""

    obj = unit.strip().lower()

    if obj in {"c", "°c", "celsius"}:
        return float(value), "C"

    if obj in {"f", "°f", "fahrenheit"}:
        celsius = (float(value) - 32.0) * 5.0 / 9.0
        return round(celsius, 4), "C"

    raise ValueError(f"Unsupported temperature unit: {unit}")


def convert_wind_speed_to_mps(value: float, unit: str) -> tuple[float, str]:
    """Конвертирует скорость ветра в м/с"""

    obj = unit.strip().lower()

    if obj in {"m/s", "mps", "meter_per_second", "meters_per_second"}:
        return float(value), "m/s"

    if obj in {"km/h", "kph", "kmh", "kilometer_per_hour", "kilometers_per_hour"}:
        mps = float(value) / 3.6
        return round(mps, 4), "m/s"

    raise ValueError(f"Unsupported wind speed unit: {unit}")


def convert_pressure_to_hpa(value: float, unit: str) -> tuple[float, str]:
    """Конвертирует давление в кПа"""

    obj = unit.strip().lower()

    if obj in {"hpa"}:
        return float(value), "hPa"

    if obj in {"pa"}:
        hpa = float(value) / 100.0
        return round(hpa, 4), "hPa"

    raise ValueError(f"Unsupported pressure unit: {unit}")


def convert_humidity_to_percent(value: float, unit: str) -> tuple[float, str]:
    """Конвертация влажность в проценты"""

    obj = unit.strip().lower()

    if obj in {"%", "percent"}:
        return float(value), "%"

    raise ValueError(f"Unsupported humidity unit: {unit}")


def convert_precipitation_to_mm(value: float, unit: str) -> tuple[float, str]:
    """Конвертирует осадки в мм"""

    obj = unit.strip().lower()

    if obj in {"mm", "millimeter", "millimeters"}:
        return float(value), "mm"

    raise ValueError(f"Unsupported precipitation unit: {unit}")


def normalize_value_and_unit(metric_type: str, value: float, unit: str) -> tuple[float, str]:
    """Нормализует значение и тип метрики"""

    metric = normalize_metric_type(metric_type)

    if metric == "temperature":
        return convert_temperature_to_celsius(value, unit)

    if metric == "wind_speed":
        return convert_wind_speed_to_mps(value, unit)

    if metric == "pressure":
        return convert_pressure_to_hpa(value, unit)

    if metric == "humidity":
        return convert_humidity_to_percent(value, unit)

    if metric == "precipitation":
        return convert_precipitation_to_mm(value, unit)

    raise ValueError(f"Unsupported metric type: {metric_type}")


def normalize_forecast(raw: ForecastRawEvent) -> NormalizedForecastRecord:
    """Нормализует forecast"""

    timezone_name = normalize_timezone_name(raw.timezone)
    metric_type = normalize_metric_type(raw.metric_type)
    normalized_value, normalized_unit = normalize_value_and_unit(
        metric_type=metric_type,
        value=raw.value,
        unit=raw.unit,
    )

    return NormalizedForecastRecord(
        event_id=raw.event_id,
        source_name=raw.source_name,
        schema_version=raw.schema_version,
        station_id=raw.station_id,
        region_id=raw.region_id,
        timezone=timezone_name,
        forecast_created_at=to_utc(raw.forecast_created_at, timezone_name),
        forecast_for_time=to_utc(raw.forecast_for_time, timezone_name),
        metric_type=metric_type,
        predicted_value=normalized_value,
        unit=normalized_unit,
        ingested_at=to_utc(raw.ingested_at, timezone_name),
        normalized_at=datetime.now(timezone.utc),
        raw_s3_key=raw.raw_s3_key,
    )


def normalize_actual(raw: ActualRawEvent) -> NormalizedActualRecord:
    """Нормализует actual"""

    metric_type = normalize_metric_type(raw.metric_type)
    normalized_value, normalized_unit = normalize_value_and_unit(
        metric_type=metric_type,
        value=raw.value,
        unit=raw.unit,
    )

    return NormalizedActualRecord(
        event_id=raw.event_id,
        source_name=raw.source_name,
        schema_version=raw.schema_version,
        station_id=raw.station_id,
        region_id=raw.region_id,
        sensor_id=raw.sensor_id,
        measured_at=to_utc(raw.measured_at),
        metric_type=metric_type,
        actual_value=normalized_value,
        unit=normalized_unit,
        ingested_at=to_utc(raw.ingested_at),
        normalized_at=datetime.now(timezone.utc),
        raw_s3_key=raw.raw_s3_key,
    )
