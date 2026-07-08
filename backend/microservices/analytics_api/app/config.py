from __future__ import annotations

import os


class Config:
    CLICKHOUSE_HOST = os.environ["CLICKHOUSE_HOST"]
    CLICKHOUSE_HTTP_PORT = int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123"))
    CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "weather")
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPICS = os.getenv("KAFKA_TOPICS", "weather.dm.ready,weather.pipeline.failed")
    KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "analytics-api")
    KAFKA_NEED_INFO_TOPIC = "weather.need_info"
    KAFKA_PIPELINE_FAILED_TOPIC = "weather.pipeline.failed"

    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    REGIONS_API_URL = os.getenv("REGIONS_API_URL", "http://regions-api:8000")

    REQUEST_TIMEOUT_SECONDS = int(os.getenv("ANALYTICS_REQUEST_TIMEOUT_SECONDS", "600"))
    TIMEOUT_SWEEP_INTERVAL_SECONDS = 30
    SSE_POLL_INTERVAL_SECONDS = 1.0

    SOURCE_NAME = "analytics_api"


config = Config()
