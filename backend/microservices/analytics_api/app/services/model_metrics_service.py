from __future__ import annotations

from app.clients.clickhouse_client import ClickHouseClient


class ModelMetricsService:
    """POST /metrics/model has no station/region filter — always
    synchronous, same reasoning as TopErrorsService."""

    def __init__(self, *, clickhouse: ClickHouseClient) -> None:
        self._clickhouse = clickhouse

    async def get_model_metrics(self, *, date_from: str, date_to: str) -> dict:
        data = await self._clickhouse.get_model_metrics(date_from=date_from, date_to=date_to)
        return {"status": "ready", "data": data}
