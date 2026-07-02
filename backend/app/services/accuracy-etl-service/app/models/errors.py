from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ForecastErrorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_event_id: UUID
    actual_event_id: UUID

    station_id: str
    region_id: str
    sensor_id: str | None = None

    source_name: str
    schema_version: str

    metric_type: str = Field(..., examples=["temperature"])
    unit: str = Field(..., examples=["C"])

    forecast_created_at: datetime
    forecast_for_time: datetime
    measured_at: datetime

    predicted_value: float
    actual_value: float

    abs_error: float
    relative_error: float | None = None
    horizon_hours: int

    ingested_at: datetime
    calculated_at: datetime

    forecast_raw_s3_key: str
    actual_raw_s3_key: str

    is_backfill: bool = False
