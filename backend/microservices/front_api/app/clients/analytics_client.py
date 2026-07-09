from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import config


class AnalyticsClient:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    @classmethod
    def from_env(cls) -> "AnalyticsClient":
        return cls(base_url=config.ANALYTICS_API_URL)

    async def close(self) -> None:
        await self._client.aclose()

    async def post(self, path: str, json_body: dict[str, Any]) -> tuple[int, Any]:
        response = await self._client.post(path, json=json_body)
        return response.status_code, response.json()

    async def get(self, path: str) -> tuple[int, Any]:
        response = await self._client.get(path)
        return response.status_code, response.json()

    def stream_get(self, path: str) -> "_SSEStream":
        return _SSEStream(self._client, path)


class _SSEStream:
    """Thin wrapper so callers can `async with client.stream_get(path) as resp:` and
    iterate raw bytes — keeps the SSE framing byte-for-byte instead of re-encoding
    parsed events, so front_api doesn't have to track the contract's exact frame
    format separately from analytics_api."""

    def __init__(self, client: httpx.AsyncClient, path: str) -> None:
        self._client = client
        self._path = path
        self._cm: Any = None
        self.response: httpx.Response | None = None

    async def __aenter__(self) -> "_SSEStream":
        self._cm = self._client.stream("GET", self._path)
        self.response = await self._cm.__aenter__()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self._cm.__aexit__(*exc_info)

    async def iter_bytes(self) -> AsyncIterator[bytes]:
        assert self.response is not None
        async for chunk in self.response.aiter_bytes():
            yield chunk
