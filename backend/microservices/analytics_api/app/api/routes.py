from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.clients.regions_client import RegionNotFoundError
from app.config import config
from app.data.schemas import (
    ErrorsTopRequest,
    MetricsModelRequest,
    RegionsForecastErrorsRequest,
    StationsForecastErrorsRequest,
)

router = APIRouter()


def _validation_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": message}})


def _status_response(result: dict) -> JSONResponse:
    status_code = 202 if result["status"] == "pending" else 200
    return JSONResponse(content=result, status_code=status_code)


@router.post("/regions/forecast-errors")
async def regions_forecast_errors(payload: RegionsForecastErrorsRequest, request: Request) -> JSONResponse:
    if not payload.regions:
        raise _validation_error("Field 'regions' is required")

    service = request.app.state.forecast_error_service
    try:
        result = await service.handle_regions_request(
            endpoint="regions_forecast_errors",
            regions=payload.regions,
            date_from=payload.from_,
            date_to=payload.to,
        )
    except RegionNotFoundError as exc:
        raise _validation_error(str(exc)) from exc
    return _status_response(result)


@router.post("/stations/forecast-errors")
async def stations_forecast_errors(payload: StationsForecastErrorsRequest, request: Request) -> JSONResponse:
    if not payload.stations:
        raise _validation_error("Field 'stations' is required")

    service = request.app.state.forecast_error_service
    result = await service.handle_stations_request(
        endpoint="stations_forecast_errors",
        stations=payload.stations,
        date_from=payload.from_,
        date_to=payload.to,
    )
    return _status_response(result)


@router.post("/errors/top")
async def errors_top(payload: ErrorsTopRequest, request: Request) -> JSONResponse:
    try:
        payload.validate_metric()
    except ValueError as exc:
        raise _validation_error(str(exc)) from exc

    service = request.app.state.top_errors_service
    result = await service.get_top_errors(
        metric=payload.metric, date_from=payload.from_, date_to=payload.to, limit=payload.limit
    )
    return _status_response(result)


@router.post("/metrics/model")
async def metrics_model(payload: MetricsModelRequest, request: Request) -> JSONResponse:
    service = request.app.state.model_metrics_service
    result = await service.get_model_metrics(date_from=payload.from_, date_to=payload.to)
    return _status_response(result)


@router.get("/requests/{request_id}")
async def get_request_status(request_id: str, request: Request) -> dict:
    redis_client = request.app.state.redis_client
    record = await redis_client.get_request(request_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "unknown request_id"}}
        )
    return {
        "request_id": record["request_id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "error_message": record["error_message"],
    }


def _sse_frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/requests/{request_id}/stream")
async def stream_request_status(request_id: str, request: Request) -> StreamingResponse:
    redis_client = request.app.state.redis_client

    async def event_generator():
        while True:
            record = await redis_client.get_request(request_id)
            if record is None:
                yield _sse_frame(
                    "failed",
                    {
                        "request_id": request_id,
                        "status": "failed",
                        "error_message": "unknown request_id",
                    },
                )
                return

            status = record["status"]
            if status == "pending":
                yield _sse_frame(
                    "status",
                    {"request_id": request_id, "status": "pending", "updated_at": record["updated_at"]},
                )
                await asyncio.sleep(config.SSE_POLL_INTERVAL_SECONDS)
                continue
            if status == "ready":
                yield _sse_frame(
                    "ready",
                    {"request_id": request_id, "status": "ready", "updated_at": record["updated_at"]},
                )
                return
            yield _sse_frame(
                "failed",
                {
                    "request_id": request_id,
                    "status": "failed",
                    "updated_at": record["updated_at"],
                    "error_message": record["error_message"],
                },
            )
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
