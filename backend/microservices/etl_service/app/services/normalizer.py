from __future__ import annotations

from app.data.schemas import (
    DailyWeatherRawDocument,
    NormalizedWeatherRecord,
    WeatherActualRawCreatedEvent,
)


def normalize_daily_weather_raw(
    *,
    event: WeatherActualRawCreatedEvent,
    raw_doc: DailyWeatherRawDocument,
    object_key: str,
) -> list[NormalizedWeatherRecord]:
    records: list[NormalizedWeatherRecord] = []

    for station in raw_doc.stations:
        records.append(
            NormalizedWeatherRecord(
                source_name=event.source_name,
                observation_date=raw_doc.date,
                wmo_index=station.wmo_index,
                station_name=station.name,
                country=station.country,
                min_temp=station.min_temp,
                avg_temp=station.avg_temp,
                max_temp=station.max_temp,
                precipitation=station.precipitation,
                raw_bucket=event.bucket,
                raw_object_key=object_key,
                event_id=event.event_id,
                trace_id=event.trace_id,
                event_created_at=event.created_at,
            )
        )

    return records