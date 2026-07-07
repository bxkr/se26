from __future__ import annotations

import os

import redis


class RedisProcessedEventStore:
    def __init__(
        self,
        redis_url: str | None = None,
        *,
        host: str | None = None,
        port: int | None = None,
        db: int | None = None,
        password: str | None = None,
        key_prefix: str = "etl:processed:",
        ttl_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds

        if redis_url is None:
            redis_url = os.getenv("REDIS_URL")

        if redis_url:
            self._client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
            )
        else:
            self._client = redis.Redis(
                host=host or os.getenv("REDIS_HOST", "redis"),
                port=port or int(os.getenv("REDIS_PORT", "6379")),
                db=db if db is not None else int(os.getenv("REDIS_DB", "0")),
                password=password or os.getenv("REDIS_PASSWORD"),
                decode_responses=True,
            )

    def is_processed(self, event_id: str) -> bool:
        return bool(self._client.exists(self._build_key(event_id)))

    def mark_processed(self, event_id: str) -> None:
        self._client.set(
            self._build_key(event_id),
            "1",
            ex=self._ttl_seconds,
        )

    def ping(self) -> bool:
        return bool(self._client.ping())

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def _build_key(self, event_id: str) -> str:
        return f"{self._key_prefix}{event_id}"