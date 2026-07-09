from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg

from app.config import config


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UsernameTakenError(Exception):
    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"username already taken: {username}")


class UserNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"user not found: {identifier}")


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "role": row["role"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


class PostgresClient:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def from_env(cls) -> "PostgresClient":
        pool = await asyncpg.create_pool(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            min_size=1,
            max_size=5,
        )
        return cls(pool)

    async def close(self) -> None:
        await self._pool.close()

    async def get_user_by_username(self, username: str) -> asyncpg.Record | None:
        return await self._pool.fetchrow("SELECT * FROM users WHERE username = $1", username)

    async def get_user_by_id(self, user_id: str) -> asyncpg.Record | None:
        return await self._pool.fetchrow("SELECT * FROM users WHERE id = $1", uuid.UUID(user_id))

    async def create_user(
        self, *, username: str, password_hash: str, role: str
    ) -> dict[str, Any]:
        user_id = uuid.uuid4()
        now = _now()
        try:
            row = await self._pool.fetchrow(
                """
                INSERT INTO users (id, username, password_hash, role, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, true, $5, $5)
                RETURNING *
                """,
                user_id,
                username,
                password_hash,
                role,
                now,
            )
        except asyncpg.UniqueViolationError:
            raise UsernameTakenError(username) from None
        return _row_to_dict(row)

    async def list_users(self) -> list[dict[str, Any]]:
        rows = await self._pool.fetch("SELECT * FROM users ORDER BY created_at")
        return [_row_to_dict(row) for row in rows]

    async def update_user(
        self,
        user_id: str,
        *,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        existing = await self.get_user_by_id(user_id)
        if existing is None:
            raise UserNotFoundError(user_id)
        row = await self._pool.fetchrow(
            """
            UPDATE users
            SET role = COALESCE($2, role),
                is_active = COALESCE($3, is_active),
                updated_at = $4
            WHERE id = $1
            RETURNING *
            """,
            uuid.UUID(user_id),
            role,
            is_active,
            _now(),
        )
        return _row_to_dict(row)

    async def set_password_hash(self, user_id: str, password_hash: str) -> None:
        result = await self._pool.execute(
            "UPDATE users SET password_hash = $2, updated_at = $3 WHERE id = $1",
            uuid.UUID(user_id),
            password_hash,
            _now(),
        )
        if result == "UPDATE 0":
            raise UserNotFoundError(user_id)

    async def delete_user(self, user_id: str) -> None:
        result = await self._pool.execute("DELETE FROM users WHERE id = $1", uuid.UUID(user_id))
        if result == "DELETE 0":
            raise UserNotFoundError(user_id)
