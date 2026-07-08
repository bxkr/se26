from __future__ import annotations

from datetime import date
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.config import config

TABLE = "weather.dm_fct_forecast_error_current"

ROW_COLUMNS = [
    "wmo_index",
    "day",
    "temperature_error",
    "temperature_abs_error",
    "temp_min_error",
    "temp_min_abs_error",
    "temp_max_error",
    "temp_max_abs_error",
    "precipitation_mm_error",
    "precipitation_mm_abs_error",
    "ingested_at",
]

# Allowed values for POST /errors/top's `metric` field (data/analytics_front_contract.md).
# Also doubles as the only way a column name reaches an ORDER BY clause —
# clickhouse-connect can't parametrize identifiers, so this allowlist is the
# SQL-injection guard, not just input validation.
TOP_ERROR_METRICS = {
    "temperature_error",
    "temperature_abs_error",
    "temp_min_error",
    "temp_min_abs_error",
    "temp_max_error",
    "temp_max_abs_error",
    "precipitation_mm_error",
    "precipitation_mm_abs_error",
}


def _row_to_dict(row: tuple) -> dict[str, Any]:
    values = dict(zip(ROW_COLUMNS, row))
    values["day"] = values["day"].isoformat()
    values["ingested_at"] = values["ingested_at"].isoformat()
    return values


class ClickHouseClient:
    def __init__(self, *, host: str, port: int, database: str, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._username = username
        self._password = password
        self._client: AsyncClient | None = None

    @classmethod
    def from_env(cls) -> "ClickHouseClient":
        return cls(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_HTTP_PORT,
            database=config.CLICKHOUSE_DB,
            username=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD,
        )

    async def _get_client(self) -> AsyncClient:
        if self._client is None:
            self._client = await clickhouse_connect.get_async_client(
                host=self._host,
                port=self._port,
                database=self._database,
                username=self._username,
                password=self._password,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def get_covered_days(
        self, *, wmo_indexes: list[str], date_from: str, date_to: str
    ) -> set[date]:
        """Days in [date_from, date_to] where ALL of wmo_indexes already have
        a dm_fct_forecast_error row — strict per-station coverage, not just
        "some data exists that day"."""
        client = await self._get_client()
        result = await client.query(
            f"""
            SELECT day
            FROM {TABLE}
            WHERE wmo_index IN {{wmo_indexes:Array(String)}}
              AND day BETWEEN {{date_from:Date32}} AND {{date_to:Date32}}
            GROUP BY day
            HAVING count(DISTINCT wmo_index) = {{station_count:UInt32}}
            """,
            parameters={
                "wmo_indexes": wmo_indexes,
                "date_from": date_from,
                "date_to": date_to,
                "station_count": len(wmo_indexes),
            },
        )
        return {row[0] for row in result.result_rows}

    async def get_rows(self, *, wmo_indexes: list[str], date_from: str, date_to: str) -> list[dict]:
        client = await self._get_client()
        result = await client.query(
            f"""
            SELECT {", ".join(ROW_COLUMNS)}
            FROM {TABLE}
            WHERE wmo_index IN {{wmo_indexes:Array(String)}}
              AND day BETWEEN {{date_from:Date32}} AND {{date_to:Date32}}
            ORDER BY day, wmo_index
            """,
            parameters={"wmo_indexes": wmo_indexes, "date_from": date_from, "date_to": date_to},
        )
        return [_row_to_dict(row) for row in result.result_rows]

    async def get_top_errors(self, *, metric: str, date_from: str, date_to: str, limit: int) -> list[dict]:
        if metric not in TOP_ERROR_METRICS:
            raise ValueError(f"unknown metric: {metric}")

        client = await self._get_client()
        result = await client.query(
            f"""
            SELECT {", ".join(ROW_COLUMNS)}
            FROM {TABLE}
            WHERE day BETWEEN {{date_from:Date32}} AND {{date_to:Date32}}
              AND {metric} IS NOT NULL
            ORDER BY {metric} DESC
            LIMIT {{limit:UInt32}}
            """,
            parameters={"date_from": date_from, "date_to": date_to, "limit": limit},
        )
        return [_row_to_dict(row) for row in result.result_rows]

    async def get_model_metrics(self, *, date_from: str, date_to: str) -> dict:
        client = await self._get_client()
        result = await client.query(
            f"""
            SELECT
                count() AS rows_count,
                avg(temperature_abs_error) AS temperature_mae,
                avg(temperature_error) AS temperature_bias,
                avg(temp_min_abs_error) AS temp_min_mae,
                avg(temp_min_error) AS temp_min_bias,
                avg(temp_max_abs_error) AS temp_max_mae,
                avg(temp_max_error) AS temp_max_bias,
                avg(precipitation_mm_abs_error) AS precipitation_mm_mae,
                avg(precipitation_mm_error) AS precipitation_mm_bias
            FROM {TABLE}
            WHERE day BETWEEN {{date_from:Date32}} AND {{date_to:Date32}}
            """,
            parameters={"date_from": date_from, "date_to": date_to},
        )
        columns = result.column_names
        row = result.result_rows[0]
        return dict(zip(columns, row))
