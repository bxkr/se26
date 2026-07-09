from __future__ import annotations

import os


class Config:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "weather")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "weather")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "weather")

    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    ANALYTICS_API_URL = os.getenv("ANALYTICS_API_URL", "http://analytics-api:8000")
    REGIONS_API_URL = os.getenv("REGIONS_API_URL", "http://regions-api:8000")

    JWT_SECRET = os.environ["FRONT_API_JWT_SECRET"]
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("FRONT_API_ACCESS_TOKEN_TTL_SECONDS", "900"))
    REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("FRONT_API_REFRESH_TOKEN_TTL_SECONDS", "1209600"))

    CACHE_TTL_SECONDS = int(os.getenv("FRONT_API_CACHE_TTL_SECONDS", "300"))

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("FRONT_API_CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    COOKIE_SECURE = os.getenv("FRONT_API_COOKIE_SECURE", "false").lower() == "true"

    DEMO_USERNAME = os.getenv("FRONT_API_DEMO_USERNAME", "demo")
    DEMO_PASSWORD = os.getenv("FRONT_API_DEMO_PASSWORD", "demo12345")

    # Abuse protection. General limit covers every request past this point
    # (identified by user id once authenticated, IP before that); the login
    # limit is deliberately tighter and IP-only since it guards credential
    # stuffing / brute force before any session exists. MAX_REQUEST_RANGE_DAYS
    # rejects oversized date ranges here, before they reach analytics_api/
    # ClickHouse or trigger a Kafka backfill — analytics_api's own
    # ANALYTICS_MAX_REQUEST_DAYS (365) is a much looser backstop, not the
    # primary guard.
    RATE_LIMIT_REQUESTS = int(os.getenv("FRONT_API_RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("FRONT_API_RATE_LIMIT_WINDOW_SECONDS", "60"))

    LOGIN_RATE_LIMIT_REQUESTS = int(os.getenv("FRONT_API_LOGIN_RATE_LIMIT_REQUESTS", "10"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("FRONT_API_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

    # Kept generous enough (well under analytics_api's 365-day backstop) that
    # legitimate exploration in the frontend's date pickers never hits this —
    # see MAX_REQUEST_RANGE_DAYS in frontend/src/lib/constants.ts, which
    # mirrors this default to pre-clamp the UI instead of round-tripping a
    # 400.
    MAX_REQUEST_RANGE_DAYS = int(os.getenv("FRONT_API_MAX_REQUEST_RANGE_DAYS", "180"))


config = Config()
