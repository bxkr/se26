from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth.dependencies import get_current_user
from app.config import config
from app.schemas import (
    ErrorsTopRequest,
    MetricsModelRequest,
    RegionsForecastErrorsRequest,
    StationsForecastErrorsRequest,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _cache_key(path: str, body: dict) -> str:
    body_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return f"{path}:{body_hash}"


async def _cached_proxy_post(request: Request, path: str, body: dict) -> JSONResponse:
    redis_client = request.app.state.redis_client
    cache_key = _cache_key(path, body)

    cached = await redis_client.get_cached(cache_key)
    if cached is not None:
        return JSONResponse(content=cached, status_code=200)

    analytics_client = request.app.state.analytics_client
    status_code, result = await analytics_client.post(path, body)

    if status_code == 200 and result.get("status") != "pending":
        await redis_client.set_cached(cache_key, result, ttl=config.CACHE_TTL_SECONDS)

    return JSONResponse(content=result, status_code=status_code)


@router.post("/regions/forecast-errors")
async def regions_forecast_errors(payload: RegionsForecastErrorsRequest, request: Request) -> JSONResponse:
    return await _cached_proxy_post(
        request, "/regions/forecast-errors", payload.model_dump(by_alias=True)
    )


@router.post("/stations/forecast-errors")
async def stations_forecast_errors(payload: StationsForecastErrorsRequest, request: Request) -> JSONResponse:
    return await _cached_proxy_post(
        request, "/stations/forecast-errors", payload.model_dump(by_alias=True)
    )


@router.post("/errors/top")
async def errors_top(payload: ErrorsTopRequest, request: Request) -> JSONResponse:
    return await _cached_proxy_post(request, "/errors/top", payload.model_dump(by_alias=True))


@router.post("/metrics/model")
async def metrics_model(payload: MetricsModelRequest, request: Request) -> JSONResponse:
    return await _cached_proxy_post(request, "/metrics/model", payload.model_dump(by_alias=True))


@router.get("/stations/search")
async def stations_search(q: str, request: Request) -> JSONResponse:
    regions_client = request.app.state.regions_client
    results = await regions_client.search_stations(q=q, limit=20)
    return JSONResponse(content=results, status_code=200)


@router.get("/requests/{request_id}")
async def get_request_status(request_id: str, request: Request) -> JSONResponse:
    analytics_client = request.app.state.analytics_client
    status_code, result = await analytics_client.get(f"/requests/{request_id}")
    return JSONResponse(content=result, status_code=status_code)


@router.get("/requests/{request_id}/stream")
async def stream_request_status(request_id: str, request: Request) -> StreamingResponse:
    analytics_client = request.app.state.analytics_client

    async def event_generator():
        async with analytics_client.stream_get(f"/requests/{request_id}/stream") as stream:
            async for chunk in stream.iter_bytes():
                yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
