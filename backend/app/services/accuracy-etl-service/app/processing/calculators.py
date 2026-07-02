from datetime import datetime, timezone

from app.models.errors import ForecastErrorRecord
from app.models.normalized_events import (
    NormalizedActualRecord,
    NormalizedForecastRecord,
)


def calculate_abs_error(predicted_value: float, actual_value: float) -> float:
    """Подсчет абсолютной ошибки"""

    return round(abs(predicted_value - actual_value), 4)


def calculate_relative_error(predicted_value: float, actual_value: float) -> float | None:
    """Подсчет относительной ошибки"""

    if actual_value == 0:
        return None

    relative_error = abs(predicted_value - actual_value) / abs(actual_value)
    return round(relative_error, 6)


def calculate_horizon_hours(
    forecast_created_at: datetime,
    forecast_for_time: datetime,
) -> int:
    """Горизонт прогноза в часах. (UTC)"""

    delta_seconds = (forecast_for_time - forecast_created_at).total_seconds()
    horizon_hours = round(delta_seconds / 3600)

    return int(horizon_hours)


def validate_records_compatibility(
    forecast: NormalizedForecastRecord,
    actual: NormalizedActualRecord,
) -> None:
    """Проверка совместимости записей"""

    if forecast.station_id != actual.station_id:
        raise ValueError(
            f"Station mismatch: forecast={forecast.station_id}, actual={actual.station_id}"
        )

    if forecast.region_id != actual.region_id:
        raise ValueError(
            f"Region mismatch: forecast={forecast.region_id}, actual={actual.region_id}"
        )

    if forecast.metric_type != actual.metric_type:
        raise ValueError(
            f"Metric mismatch: forecast={forecast.metric_type}, actual={actual.metric_type}"
        )

    if forecast.unit != actual.unit:
        raise ValueError(
            f"Unit mismatch: forecast={forecast.unit}, actual={actual.unit}"
        )


def build_forecast_error_record(
    forecast: NormalizedForecastRecord,
    actual: NormalizedActualRecord,
    is_backfill: bool = False,
) -> ForecastErrorRecord:
    """Собирает итоговую запись ошибки прогноза (forecast + actual)"""

    validate_records_compatibility(forecast, actual)

    abs_error = calculate_abs_error(
        predicted_value=forecast.predicted_value,
        actual_value=actual.actual_value,
    )

    relative_error = calculate_relative_error(
        predicted_value=forecast.predicted_value,
        actual_value=actual.actual_value,
    )

    horizon_hours = calculate_horizon_hours(
        forecast_created_at=forecast.forecast_created_at,
        forecast_for_time=forecast.forecast_for_time,
    )

    return ForecastErrorRecord(
        forecast_event_id=forecast.event_id,
        actual_event_id=actual.event_id,
        station_id=forecast.station_id,
        region_id=forecast.region_id,
        sensor_id=actual.sensor_id,
        source_name=forecast.source_name,
        schema_version=forecast.schema_version,
        metric_type=forecast.metric_type,
        unit=forecast.unit,
        forecast_created_at=forecast.forecast_created_at,
        forecast_for_time=forecast.forecast_for_time,
        measured_at=actual.measured_at,
        predicted_value=forecast.predicted_value,
        actual_value=actual.actual_value,
        abs_error=abs_error,
        relative_error=relative_error,
        horizon_hours=horizon_hours,
        is_backfill=is_backfill,
        ingested_at=max(forecast.ingested_at, actual.ingested_at),
        calculated_at=datetime.now(timezone.utc),
        forecast_raw_s3_key=forecast.raw_s3_key,
        actual_raw_s3_key=actual.raw_s3_key,
    )
