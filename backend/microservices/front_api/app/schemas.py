from __future__ import annotations

from pydantic import BaseModel, Field


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


class MetricsModelRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}
