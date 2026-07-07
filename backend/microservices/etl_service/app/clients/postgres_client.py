from __future__ import annotations

import os
from typing import Any, Sequence

import psycopg2
from psycopg2.extras import execute_batch


class PostgresClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        dbname: str,
        user: str,
        password: str,
    ) -> None:
        self._host = host
        self._port = port
        self._dbname = dbname
        self._user = user
        self._password = password
        self._connection = None

    @classmethod
    def from_env(cls) -> "PostgresClient":
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )

    def get_connection(self):
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self._host,
                port=self._port,
                dbname=self._dbname,
                user=self._user,
                password=self._password,
            )
            self._connection.autocommit = False

        return self._connection

    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] | None = None) -> None:
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def execute_many(
        self,
        sql: str,
        payload: list[dict[str, Any]],
        *,
        page_size: int = 500,
    ) -> None:
        if not payload:
            return

        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                execute_batch(cursor, sql, payload, page_size=page_size)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def close(self) -> None:
        if self._connection is not None and not self._connection.closed:
            self._connection.close()