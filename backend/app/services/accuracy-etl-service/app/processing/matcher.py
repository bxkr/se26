from datetime import datetime
from typing import Iterable

from app.models.normalized_events import (
    NormalizedActualRecord,
    NormalizedForecastRecord,
)


def truncate_to_hour(dt: datetime) -> datetime:
    """Обрезает datetime до начала часа (UTC)"""

    return dt.replace(minute=0, second=0, microsecond=0)


def build_match_key(
    station_id: str,
    region_id: str,
    metric_type: str,
    unit: str,
    dt: datetime,
) -> tuple[str, str, str, str, datetime]:
    """Строит ключ матчинга по станции, региону, метрике, единице и часовому интервалу"""

    return (
        station_id,
        region_id,
        metric_type,
        unit,
        truncate_to_hour(dt),
    )


def get_forecast_match_key(forecast: NormalizedForecastRecord) -> tuple[str, str, str, str, datetime]:
    """Строит ключ матчинга для forecast"""

    return build_match_key(
        station_id=forecast.station_id,
        region_id=forecast.region_id,
        metric_type=forecast.metric_type,
        unit=forecast.unit,
        dt=forecast.forecast_for_time,
    )


def get_actual_match_key(actual: NormalizedActualRecord) -> tuple[str, str, str, str, datetime]:
    """Строит ключ матчинга для actual"""

    return build_match_key(
        station_id=actual.station_id,
        region_id=actual.region_id,
        metric_type=actual.metric_type,
        unit=actual.unit,
        dt=actual.measured_at,
    )


def can_match_forecast_and_actual(
    forecast: NormalizedForecastRecord,
    actual: NormalizedActualRecord,
) -> bool:
    """Проверяет, подходят ли forecast и actual для матчинга"""

    return get_forecast_match_key(forecast) == get_actual_match_key(actual)


def find_matching_actual(
    forecast: NormalizedForecastRecord,
    actual_records: Iterable[NormalizedActualRecord],
) -> NormalizedActualRecord | None:
    """Ищет подходящий actual для одного forecast"""

    best_actual: NormalizedActualRecord | None = None
    best_distance: float | None = None
    
    for actual in actual_records:
        if not can_match_forecast_and_actual(forecast, actual):
            continue

        distance = abs((actual.measured_at - forecast.forecast_for_time).total_seconds())
        if best_actual is None:
            best_actual = actual
            best_distance = distance
            continue

        if distance < best_distance:
            best_actual = actual
            best_distance = distance
            continue

        if distance == best_distance and actual.measured_at < best_actual.measured_at:
            best_actual = actual
            best_distance = distance

    return best_actual


def find_matching_forecast(
    actual: NormalizedActualRecord,
    forecast_records: Iterable[NormalizedForecastRecord],
) -> NormalizedForecastRecord | None:
    """Ищет подходящий forecast для одного actual"""

    best_forecast: NormalizedForecastRecord | None = None
    best_distance: float | None = None

    for forecast in forecast_records:
        if not can_match_forecast_and_actual(forecast, actual):
            continue

        distance = abs((forecast.forecast_for_time - actual.measured_at).total_seconds())
        if best_forecast is None:
            best_forecast = forecast
            best_distance = distance
            continue

        if distance < best_distance:
            best_forecast = forecast
            best_distance = distance
            continue

        if distance == best_distance and forecast.forecast_for_time < best_forecast.forecast_for_time:
            best_forecast = forecast
            best_distance = distance

    return best_forecast


def group_actuals_by_match_key(
    actual_records: Iterable[NormalizedActualRecord],
) -> dict[tuple[str, str, str, str, datetime], list[NormalizedActualRecord]]:
    """Группирует actual записи по match key"""

    grouped: dict[tuple[str, str, str, str, datetime], list[NormalizedActualRecord]] = {}

    for actual in actual_records:
        key = get_actual_match_key(actual)
        grouped.setdefault(key, []).append(actual)

    return grouped


def find_matching_actual_fast(
    forecast: NormalizedForecastRecord,
    grouped_actuals: dict[tuple[str, str, str, str, datetime], list[NormalizedActualRecord]],
) -> NormalizedActualRecord | None:
    """Быстрый поиск actual, если actual уже заранее сгруппированы по match key"""

    key = get_forecast_match_key(forecast)
    candidates = grouped_actuals.get(key)

    if not candidates:
        return None
    
    best_actual: NormalizedActualRecord | None = None
    best_distance: float | None = None

    for actual in candidates:
        distance = abs((actual.measured_at - forecast.forecast_for_time).total_seconds())
        if best_actual is None:
            best_actual = actual
            best_distance = distance
            continue

        if distance < best_distance:
            best_actual = actual
            best_distance = distance
            continue

        if distance == best_distance and actual.measured_at < best_actual.measured_at:
            best_actual = actual
            best_distance = distance

    return best_actual
