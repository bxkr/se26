from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from app.clients.clickhouse_client import ClickHouseClient
from app.clients.kafka_client import KafkaProducerClient, utc_now_iso
from app.clients.redis_client import RedisClient
from app.clients.regions_client import RegionsClient
from app.config import config

# dm_fct_forecast_error is an inner join of actual x forecast; a missing day
# could be missing on either side (or both), so we always request both —
# predict_fetcher doesn't exist yet, so the forecast side just stays pending
# until the timeout sweep fails it. That's accepted behavior, not a bug.
DATASET_TYPES = ("actual", "forecast")


def _daterange(date_from: str, date_to: str) -> list[date]:
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _contiguous_ranges(days: list[date]) -> list[tuple[date, date]]:
    if not days:
        return []
    ordered = sorted(days)
    ranges: list[tuple[date, date]] = []
    range_start = ordered[0]
    prev = ordered[0]
    for day in ordered[1:]:
        if (day - prev).days > 1:
            ranges.append((range_start, prev))
            range_start = day
        prev = day
    ranges.append((range_start, prev))
    return ranges


class ForecastErrorService:
    def __init__(
        self,
        *,
        clickhouse: ClickHouseClient,
        kafka_producer: KafkaProducerClient,
        redis_client: RedisClient,
        regions_client: RegionsClient,
    ) -> None:
        self._clickhouse = clickhouse
        self._kafka_producer = kafka_producer
        self._redis = redis_client
        self._regions = regions_client

    async def handle_stations_request(
        self, *, endpoint: str, stations: list[str], date_from: str, date_to: str
    ) -> dict:
        wmo_indexes = list(dict.fromkeys(stations))
        return await self._handle(
            endpoint=endpoint, wmo_indexes=wmo_indexes, date_from=date_from, date_to=date_to
        )

    async def handle_regions_request(
        self, *, endpoint: str, regions: list[str], date_from: str, date_to: str
    ) -> dict:
        wmo_indexes = await self._regions.get_wmo_indexes_for_regions(regions)
        return await self._handle(
            endpoint=endpoint, wmo_indexes=wmo_indexes, date_from=date_from, date_to=date_to
        )

    async def _handle(self, *, endpoint: str, wmo_indexes: list[str], date_from: str, date_to: str) -> dict:
        all_days = _daterange(date_from, date_to)
        covered = await self._clickhouse.get_covered_days(
            wmo_indexes=wmo_indexes, date_from=date_from, date_to=date_to
        )
        missing_days = [d for d in all_days if d not in covered]

        if not missing_days:
            rows = await self._clickhouse.get_rows(
                wmo_indexes=wmo_indexes, date_from=date_from, date_to=date_to
            )
            return {"status": "ready", "data": {"rows": rows}}

        trace_ids = await self._request_missing_ranges(wmo_indexes=wmo_indexes, missing_days=missing_days)

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        await self._redis.create_request(
            request_id=request_id,
            endpoint=endpoint,
            query={"wmo_indexes": wmo_indexes, "date_from": date_from, "date_to": date_to},
            pending_trace_ids=trace_ids,
        )
        for trace_id in set(trace_ids):
            await self._redis.add_waiter(trace_id, request_id, ttl=config.REQUEST_TIMEOUT_SECONDS)

        return {"status": "pending", "request_id": request_id}

    async def _request_missing_ranges(self, *, wmo_indexes: list[str], missing_days: list[date]) -> list[str]:
        trace_ids: list[str] = []
        for range_start, range_end in _contiguous_ranges(missing_days):
            for dataset_type in DATASET_TYPES:
                trace_id = await self._ensure_fetch_in_flight(
                    dataset_type=dataset_type,
                    wmo_indexes=wmo_indexes,
                    range_start=range_start,
                    range_end=range_end,
                )
                trace_ids.append(trace_id)
        return trace_ids

    async def _ensure_fetch_in_flight(
        self, *, dataset_type: str, wmo_indexes: list[str], range_start: date, range_end: date
    ) -> str:
        # Checking only the range's first (station, day) as a representative
        # dedup signal — good enough to avoid the common case of duplicate
        # concurrent requests, not a strict distributed lock over the whole
        # range (see plan: acceptable simplification for this scope).
        existing_owner = await self._redis.get_lock_owner(dataset_type, wmo_indexes[0], range_start)
        if existing_owner is not None:
            return existing_owner

        trace_id = str(uuid.uuid4())
        days = _daterange(range_start.isoformat(), range_end.isoformat())
        for wmo_index in wmo_indexes:
            for day in days:
                await self._redis.acquire_lock(
                    dataset_type, wmo_index, day, trace_id, ttl=config.REQUEST_TIMEOUT_SECONDS
                )

        event = {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "event_type": "weather.need_info",
            "dataset_type": dataset_type,
            "requested_by": config.SOURCE_NAME,
            "date_from": range_start.isoformat(),
            "date_to": range_end.isoformat(),
            "wmo_indexes": wmo_indexes,
            "reason": "missing_forecast_error_data",
            "schema_version": 1,
            "created_at": utc_now_iso(),
        }
        self._kafka_producer.send(config.KAFKA_NEED_INFO_TOPIC, event)
        return trace_id
