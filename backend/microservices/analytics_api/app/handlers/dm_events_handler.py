from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.clients.clickhouse_client import ClickHouseClient
from app.clients.redis_client import RedisClient
from app.config import config

logger = logging.getLogger("analytics_api.dm_events_handler")


class DmEventsHandler:
    """Consumes weather.dm.ready / weather.pipeline.failed on a background
    thread (kafka-python is sync) and resolves pending analytics_api
    requests waiting on those trace_ids. The Redis/ClickHouse clients are
    async and bound to the main asyncio event loop, so each message is
    bridged onto that loop via run_coroutine_threadsafe rather than given
    its own throwaway loop — keeps the same connection pool everywhere.
    """

    def __init__(
        self, *, redis_client: RedisClient, clickhouse: ClickHouseClient, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._redis = redis_client
        self._clickhouse = clickhouse
        self._loop = loop

    def handle_message(self, payload: bytes | str | dict, topic: str) -> None:
        try:
            if isinstance(payload, (bytes, bytearray)):
                event = json.loads(payload.decode("utf-8"))
            elif isinstance(payload, str):
                event = json.loads(payload)
            else:
                event = payload
        except Exception as exc:
            logger.error("failed to parse dm event payload | topic=%s error=%s", topic, exc)
            return

        future = asyncio.run_coroutine_threadsafe(self._handle_async(event, topic), self._loop)
        try:
            future.result(timeout=30)
        except Exception as exc:
            logger.error(
                "failed to handle dm event | topic=%s trace_id=%s error=%s",
                topic,
                event.get("trace_id"),
                exc,
            )

    async def _handle_async(self, event: dict[str, Any], topic: str) -> None:
        trace_id = event.get("trace_id")
        if not trace_id:
            return

        waiters = await self._redis.get_waiters(trace_id)
        if not waiters:
            return

        if topic == "weather.dm.ready":
            for request_id in waiters:
                await self._on_trace_resolved(request_id, trace_id)
        elif topic == "weather.pipeline.failed":
            reason = event.get("reason", "unknown")
            details = event.get("details", "")
            message = f"upstream failure ({event.get('stage', '?')}): {reason} — {details}"
            for request_id in waiters:
                await self._redis.mark_request_failed(request_id, message)

    async def _on_trace_resolved(self, request_id: str, trace_id: str) -> None:
        record = await self._redis.remove_pending_trace(request_id, trace_id)
        if record is None or record["status"] != "pending":
            return
        if record["pending_trace_ids"]:
            return  # still waiting on other trace_ids for this request

        query = record["query"]
        rows = await self._clickhouse.get_rows(
            wmo_indexes=query["wmo_indexes"], date_from=query["date_from"], date_to=query["date_to"]
        )
        await self._redis.mark_request_ready(request_id, {"rows": rows})


async def timeout_sweep_loop(redis_client: RedisClient) -> None:
    while True:
        await asyncio.sleep(config.TIMEOUT_SWEEP_INTERVAL_SECONDS)
        try:
            await _sweep_once(redis_client)
        except Exception:
            logger.exception("timeout sweep failed")


async def _sweep_once(redis_client: RedisClient) -> None:
    now = datetime.now(timezone.utc)
    for request_id in await redis_client.list_pending_request_ids():
        record = await redis_client.get_request(request_id)
        if record is None or record["status"] != "pending":
            continue

        updated_at = datetime.fromisoformat(record["updated_at"].replace("Z", "+00:00"))
        if (now - updated_at).total_seconds() > config.REQUEST_TIMEOUT_SECONDS:
            await redis_client.mark_request_failed(
                request_id,
                "timed out waiting for upstream data (forecast side needs predict_fetcher, "
                "which may not exist yet — this is expected until it's built)",
            )
