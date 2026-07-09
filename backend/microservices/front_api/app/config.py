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


config = Config()
