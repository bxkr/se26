from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ForecastRawEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    source_type: str = Field(..., examples=["forecast_api"])
    source_name: str = Field(..., examples=["openweather"])
    ingested_at: datetime
    schema_version: str = Field(..., examples=["1"])
    station_id: str
    region_id: str

    forecast_created_at: datetime
    forecast_for_time: datetime

    metric_type: str = Field(..., examples=["temperature"])
    value: float
    unit: str = Field(..., examples=["C"])

    raw_s3_key: str
    timezone: str = Field(..., examples=["Europe/Moscow"])


class ActualRawEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    source_type: str = Field(..., examples=["weather_station"])
    source_name: str = Field(..., examples=["station_gateway"])
    ingested_at: datetime
    schema_version: str = Field(..., examples=["1"])
    station_id: str
    region_id: str

    sensor_id: str
    measured_at: datetime

    metric_type: str = Field(..., examples=["temperature"])
    value: float
    unit: str = Field(..., examples=["C"])

    raw_s3_key: str
