from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.clients.clickhouse_client import ClickHouseClient
from app.clients.kafka_client import KafkaConsumerClient, KafkaProducerClient
from app.clients.redis_client import RedisClient
from app.clients.regions_client import RegionsClient
from app.handlers.dm_events_handler import DmEventsHandler, timeout_sweep_loop
from app.services.forecast_error_service import ForecastErrorService
from app.services.model_metrics_service import ModelMetricsService
from app.services.top_errors_service import TopErrorsService


class AppLogger:
    """kafka_client.py's clients call logger.info(message, **kwargs) with
    arbitrary structured kwargs — the stdlib Logger doesn't accept that
    (TypeError: unexpected keyword argument), so it needs this formatting
    adapter, not a bare logging.getLogger(...)."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(self._format(message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(self._format(message, kwargs))

    @staticmethod
    def _format(message: str, kwargs: dict[str, Any]) -> str:
        if not kwargs:
            return message
        parts = [f"{key}={value}" for key, value in kwargs.items()]
        return f"{message} | " + " ".join(parts)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = AppLogger("analytics_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    clickhouse = ClickHouseClient.from_env()
    redis_client = RedisClient.from_env()
    regions_client = RegionsClient.from_env()
    kafka_producer = KafkaProducerClient.from_env(logger=logger)

    app.state.redis_client = redis_client
    app.state.forecast_error_service = ForecastErrorService(
        clickhouse=clickhouse,
        kafka_producer=kafka_producer,
        redis_client=redis_client,
        regions_client=regions_client,
    )
    app.state.top_errors_service = TopErrorsService(clickhouse=clickhouse, regions_client=regions_client)
    app.state.model_metrics_service = ModelMetricsService(clickhouse=clickhouse)

    loop = asyncio.get_running_loop()
    dm_handler = DmEventsHandler(
        redis_client=redis_client, clickhouse=clickhouse, regions_client=regions_client, loop=loop
    )
    kafka_consumer = KafkaConsumerClient.from_env(logger=logger)

    consumer_thread = threading.Thread(
        target=kafka_consumer.consume_forever, args=(dm_handler.handle_message,), daemon=True
    )
    consumer_thread.start()
    logger.info("dm events kafka consumer thread started")

    sweep_task = asyncio.create_task(timeout_sweep_loop(redis_client))

    try:
        yield
    finally:
        kafka_consumer.stop()
        kafka_producer.close()
        sweep_task.cancel()
        await regions_client.close()
        await clickhouse.close()
        await redis_client.close()


app = FastAPI(title="analytics_api", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first_error.get("loc", []) if part != "body")
    message = f"Field '{field}' {first_error.get('msg', 'is invalid')}" if field else "Invalid request body"
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "VALIDATION_ERROR", "message": message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # routes.py raises HTTPException(detail={"error": {...}}) matching the
    # contract's flat error shape directly — FastAPI's default handler would
    # wrap that in {"detail": {"error": {...}}}, which isn't what the
    # contract documents. Pass dict details through as-is; only fall back to
    # the {"detail": ...} shape for exceptions we didn't build ourselves.
    content = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
