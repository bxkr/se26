from __future__ import annotations

from typing import Any

from app.data.schemas import NormalizedWeatherRecord


class WeatherActualWriter:
    def __init__(
        self,
        postgres_client: Any,
        *,
        table_name: str = "weather_actual",
        logger: Any | None = None,
    ) -> None:
        self._postgres_client = postgres_client
        self._table_name = table_name
        self._logger = logger

    def write(self, records: list[NormalizedWeatherRecord]) -> None:
        if not records:
            self._log_info("no normalized records to write")
            return

        sql = f"""
        INSERT INTO {self._table_name} (
            source_name,
            observation_date,
            wmo_index,
            station_name,
            country,
            min_temp,
            avg_temp,
            max_temp,
            precipitation,
            raw_bucket,
            raw_object_key,
            event_id,
            trace_id,
            event_created_at
        )
        VALUES (
            %(source_name)s,
            %(observation_date)s,
            %(wmo_index)s,
            %(station_name)s,
            %(country)s,
            %(min_temp)s,
            %(avg_temp)s,
            %(max_temp)s,
            %(precipitation)s,
            %(raw_bucket)s,
            %(raw_object_key)s,
            %(event_id)s,
            %(trace_id)s,
            %(event_created_at)s
        )
        ON CONFLICT (source_name, observation_date, wmo_index)
        DO UPDATE SET
            station_name = EXCLUDED.station_name,
            country = EXCLUDED.country,
            min_temp = EXCLUDED.min_temp,
            avg_temp = EXCLUDED.avg_temp,
            max_temp = EXCLUDED.max_temp,
            precipitation = EXCLUDED.precipitation,
            raw_bucket = EXCLUDED.raw_bucket,
            raw_object_key = EXCLUDED.raw_object_key,
            event_id = EXCLUDED.event_id,
            trace_id = EXCLUDED.trace_id,
            event_created_at = EXCLUDED.event_created_at
        """

        payload = [record.to_dict() for record in records]
        self._execute_many(sql, payload)

        self._log_info(
            "normalized weather records written",
            record_count=len(records),
            table_name=self._table_name,
        )

    def _execute_many(self, sql: str, payload: list[dict[str, Any]]) -> None:
        if hasattr(self._postgres_client, "execute_many"):
            self._postgres_client.execute_many(sql, payload)
            return

        if hasattr(self._postgres_client, "executemany"):
            self._postgres_client.executemany(sql, payload)
            return

        if hasattr(self._postgres_client, "get_connection"):
            connection = self._postgres_client.get_connection()
            with connection.cursor() as cursor:
                cursor.executemany(sql, payload)
            connection.commit()
            return

        if hasattr(self._postgres_client, "connection"):
            connection = self._postgres_client.connection
            with connection.cursor() as cursor:
                cursor.executemany(sql, payload)
            connection.commit()
            return

        raise AttributeError(
            "postgres_client must expose one of: "
            "'execute_many', 'executemany', 'get_connection()', or 'connection'"
        )

    def _log_info(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "info"):
            self._logger.info(message, **kwargs)