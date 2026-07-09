from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.config import config


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    new_password: str


# ---- dashboard proxy request bodies (mirror data/analytics_front_contract.md) ----


class _DateRangeRequest(BaseModel):
    """Rejects oversized date ranges here, before they reach analytics_api/
    ClickHouse or trigger a Kafka backfill — a request for e.g. `from=2000-01-01`
    would otherwise cost real backend work just to get validated deep inside
    the pipeline."""

    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _validate_range(self) -> "_DateRangeRequest":
        try:
            date_from = date.fromisoformat(self.from_)
            date_to = date.fromisoformat(self.to)
        except ValueError:
            raise ValueError("'from'/'to' must be dates in YYYY-MM-DD format") from None
        if date_from > date_to:
            raise ValueError("'from' must not be after 'to'")
        span_days = (date_to - date_from).days + 1
        if span_days > config.MAX_REQUEST_RANGE_DAYS:
            raise ValueError(
                f"requested range spans {span_days} days, max is {config.MAX_REQUEST_RANGE_DAYS}"
            )
        return self


class RegionsForecastErrorsRequest(_DateRangeRequest):
    regions: list[str]


class StationsForecastErrorsRequest(_DateRangeRequest):
    stations: list[str]


class ErrorsTopRequest(_DateRangeRequest):
    metric: str
    limit: int = 100


class MetricsModelRequest(_DateRangeRequest):
    pass
