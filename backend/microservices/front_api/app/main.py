from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin_routes import router as admin_router
from app.api.auth_routes import router as auth_router
from app.api.dashboard_routes import router as dashboard_router
from app.auth.security import hash_password
from app.clients.analytics_client import AnalyticsClient
from app.clients.postgres_client import PostgresClient
from app.clients.redis_client import RedisClient
from app.clients.regions_client import RegionsClient
from app.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("front_api")


async def _ensure_demo_user(postgres: PostgresClient) -> None:
    existing = await postgres.get_user_by_username(config.DEMO_USERNAME)
    if existing is not None:
        return
    await postgres.create_user(
        username=config.DEMO_USERNAME,
        password_hash=hash_password(config.DEMO_PASSWORD),
        role="user",
    )
    logger.info("seeded demo user | username=%s", config.DEMO_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    postgres = await PostgresClient.from_env()
    redis_client = RedisClient.from_env()
    analytics_client = AnalyticsClient.from_env()
    regions_client = RegionsClient.from_env()

    await _ensure_demo_user(postgres)

    app.state.postgres_client = postgres
    app.state.redis_client = redis_client
    app.state.analytics_client = analytics_client
    app.state.regions_client = regions_client

    try:
        yield
    finally:
        await postgres.close()
        await redis_client.close()
        await analytics_client.close()
        await regions_client.close()


app = FastAPI(title="front_api", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(dashboard_router)


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
    content = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
