from __future__ import annotations

from pydantic import BaseModel, Field

from app.clients.clickhouse_client import TOP_ERROR_METRICS


class RegionsForecastErrorsRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str
    regions: list[str]

    model_config = {"populate_by_name": True}


class StationsForecastErrorsRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str
    stations: list[str]

    model_config = {"populate_by_name": True}


class ErrorsTopRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str
    metric: str
    limit: int = 100

    model_config = {"populate_by_name": True}

    def validate_metric(self) -> None:
        if self.metric not in TOP_ERROR_METRICS:
            raise ValueError(f"metric must be one of {sorted(TOP_ERROR_METRICS)}")


class MetricsModelRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}
