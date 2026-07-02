from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NormalizedForecastRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    source_name: str
    schema_version: str

    station_id: str
    region_id: str
    timezone: str

    forecast_created_at: datetime
    forecast_for_time: datetime

    metric_type: str = Field(..., examples=["temperature"])
    predicted_value: float
    unit: str = Field(..., examples=["C"])

    ingested_at: datetime
    normalized_at: datetime

    raw_s3_key: str
    


class NormalizedActualRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    source_name: str
    schema_version: str

    station_id: str
    region_id: str
    sensor_id: str
    timezone: str


    measured_at: datetime

    metric_type: str = Field(..., examples=["temperature"])
    actual_value: float
    unit: str = Field(..., examples=["C"])

    ingested_at: datetime
    normalized_at: datetime

    raw_s3_key: str
