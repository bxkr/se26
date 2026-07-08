from __future__ import annotations

from app.clients.clickhouse_client import ClickHouseClient


class TopErrorsService:
    """POST /errors/top has no station/region filter, so there's no way to
    know what "missing" data would even mean — always synchronous, reads
    whatever ClickHouse already has for the date range."""

    def __init__(self, *, clickhouse: ClickHouseClient) -> None:
        self._clickhouse = clickhouse

    async def get_top_errors(self, *, metric: str, date_from: str, date_to: str, limit: int) -> dict:
        rows = await self._clickhouse.get_top_errors(
            metric=metric, date_from=date_from, date_to=date_to, limit=limit
        )
        return {"status": "ready", "data": {"metric": metric, "rows": rows}}
