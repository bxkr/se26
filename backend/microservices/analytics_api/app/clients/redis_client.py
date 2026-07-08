from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

import redis.asyncio as redis

from app.config import config

PENDING_REQUESTS_SET = "pending_requests"

# Redis key TTL is just housekeeping cleanup, deliberately decoupled from
# config.REQUEST_TIMEOUT_SECONDS (the business-logic "give up and mark
# failed" threshold the sweep uses). Re-deriving TTL from the *live* config
# on every _save_request call meant a config change picked up by a new pod
# could retroactively shrink the TTL of already-in-flight records the next
# time they were touched — caught this in testing by temporarily lowering
# the timeout and watching an in-flight request's key vanish early.
REQUEST_KEY_TTL_SECONDS = 3600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RedisClient:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> "RedisClient":
        client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
        return cls(client)

    async def close(self) -> None:
        await self._client.aclose()

    # ---- request state -----------------------------------------------

    async def create_request(
        self, *, request_id: str, endpoint: str, query: dict[str, Any], pending_trace_ids: list[str]
    ) -> None:
        now = _now_iso()
        record = {
            "request_id": request_id,
            "endpoint": endpoint,
            "query": query,
            "status": "pending",
            "pending_trace_ids": pending_trace_ids,
            "result": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        await self._client.set(f"req:{request_id}", json.dumps(record), ex=REQUEST_KEY_TTL_SECONDS)
        await self._client.sadd(PENDING_REQUESTS_SET, request_id)

    async def get_request(self, request_id: str) -> dict[str, Any] | None:
        raw = await self._client.get(f"req:{request_id}")
        return json.loads(raw) if raw else None

    async def _save_request(self, record: dict[str, Any]) -> None:
        record["updated_at"] = _now_iso()
        await self._client.set(
            f"req:{record['request_id']}", json.dumps(record), ex=REQUEST_KEY_TTL_SECONDS
        )

    async def mark_request_ready(self, request_id: str, result: Any) -> None:
        record = await self.get_request(request_id)
        if record is None:
            return
        record["status"] = "ready"
        record["result"] = result
        await self._save_request(record)
        await self._client.srem(PENDING_REQUESTS_SET, request_id)

    async def mark_request_failed(self, request_id: str, error_message: str) -> None:
        record = await self.get_request(request_id)
        if record is None:
            return
        record["status"] = "failed"
        record["error_message"] = error_message
        await self._save_request(record)
        await self._client.srem(PENDING_REQUESTS_SET, request_id)

    async def remove_pending_trace(self, request_id: str, trace_id: str) -> dict[str, Any] | None:
        """Remove trace_id from a request's wait list. Returns the updated
        record if the request still exists (caller checks whether
        pending_trace_ids is now empty to decide if it's ready)."""
        record = await self.get_request(request_id)
        if record is None or record["status"] != "pending":
            return record
        record["pending_trace_ids"] = [t for t in record["pending_trace_ids"] if t != trace_id]
        await self._save_request(record)
        return record

    async def list_pending_request_ids(self) -> list[str]:
        return list(await self._client.smembers(PENDING_REQUESTS_SET))

    # ---- dedup locks + waiters -----------------------------------------

    def _lock_key(self, dataset_type: str, wmo_index: str, day: date | str) -> str:
        return f"lock:{dataset_type}:{wmo_index}:{day}"

    async def get_lock_owner(self, dataset_type: str, wmo_index: str, day: date | str) -> str | None:
        return await self._client.get(self._lock_key(dataset_type, wmo_index, day))

    async def acquire_lock(
        self, dataset_type: str, wmo_index: str, day: date | str, trace_id: str, ttl: int
    ) -> bool:
        return bool(
            await self._client.set(self._lock_key(dataset_type, wmo_index, day), trace_id, nx=True, ex=ttl)
        )

    async def add_waiter(self, trace_id: str, request_id: str, ttl: int) -> None:
        key = f"waiters:{trace_id}"
        await self._client.sadd(key, request_id)
        await self._client.expire(key, ttl)

    async def get_waiters(self, trace_id: str) -> set[str]:
        return await self._client.smembers(f"waiters:{trace_id}")
