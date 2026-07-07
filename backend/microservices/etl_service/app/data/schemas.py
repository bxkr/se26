from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class WeatherActualRawCreatedEvent:
    event_id: str
    trace_id: str
    event_type: str
    source_name: str
    bucket: str
    object_keys: list[str]
    date_from: str
    date_to: str
    schema_version: int
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeatherActualRawCreatedEvent":
        return cls(
            event_id=str(payload["event_id"]),
            trace_id=str(payload["trace_id"]),
            event_type=str(payload["event_type"]),
            source_name=str(payload["source_name"]),
            bucket=str(payload["bucket"]),
            object_keys=[str(x) for x in payload["object_keys"]],
            date_from=str(payload["date_from"]),
            date_to=str(payload["date_to"]),
            schema_version=int(payload["schema_version"]),
            created_at=str(payload["created_at"]),
        )


@dataclass(slots=True)
class RawStation:
    wmo_index: str
    name: str
    country: str
    min_temp: float | None
    avg_temp: float | None
    max_temp: float | None
    precipitation: float | None


@dataclass(slots=True)
class DailyWeatherRawDocument:
    date: str
    stations: list[RawStation]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DailyWeatherRawDocument":
        raw_stations = payload.get("stations", [])
        stations: list[RawStation] = []

        for item in raw_stations:
            stations.append(
                RawStation(
                    wmo_index=str(item["wmo_index"]),
                    name=str(item["name"]),
                    country=str(item["country"]),
                    min_temp=_to_optional_float(item.get("min_temp")),
                    avg_temp=_to_optional_float(item.get("avg_temp")),
                    max_temp=_to_optional_float(item.get("max_temp")),
                    precipitation=_to_optional_float(item.get("precipitation")),
                )
            )

        return cls(
            date=str(payload["date"]),
            stations=stations,
        )


@dataclass(slots=True)
class NormalizedWeatherRecord:
    source_name: str
    observation_date: str
    wmo_index: str
    station_name: str
    country: str
    min_temp: float | None
    avg_temp: float | None
    max_temp: float | None
    precipitation: float | None
    raw_bucket: str
    raw_object_key: str
    event_id: str
    trace_id: str
    event_created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "observation_date": self.observation_date,
            "wmo_index": self.wmo_index,
            "station_name": self.station_name,
            "country": self.country,
            "min_temp": self.min_temp,
            "avg_temp": self.avg_temp,
            "max_temp": self.max_temp,
            "precipitation": self.precipitation,
            "raw_bucket": self.raw_bucket,
            "raw_object_key": self.raw_object_key,
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "event_created_at": self.event_created_at,
        }


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)