from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.config import config

CACHE_PREFIX = "cache:"
REFRESH_PREFIX = "refresh:"


class RedisClient:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> "RedisClient":
        client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
        return cls(client)

    async def close(self) -> None:
        await self._client.aclose()

    # ---- response cache -------------------------------------------------

    async def get_cached(self, cache_key: str) -> Any | None:
        raw = await self._client.get(f"{CACHE_PREFIX}{cache_key}")
        return json.loads(raw) if raw is not None else None

    async def set_cached(self, cache_key: str, value: Any, *, ttl: int) -> None:
        await self._client.set(f"{CACHE_PREFIX}{cache_key}", json.dumps(value), ex=ttl)

    # ---- refresh-token store ---------------------------------------------

    async def store_refresh_token(self, jti: str, user_id: str, *, ttl: int) -> None:
        await self._client.set(f"{REFRESH_PREFIX}{jti}", user_id, ex=ttl)

    async def get_refresh_token_owner(self, jti: str) -> str | None:
        return await self._client.get(f"{REFRESH_PREFIX}{jti}")

    async def revoke_refresh_token(self, jti: str) -> None:
        await self._client.delete(f"{REFRESH_PREFIX}{jti}")
