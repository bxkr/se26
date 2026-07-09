from __future__ import annotations

import httpx

from app.config import config


class RegionsClient:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)

    @classmethod
    def from_env(cls) -> "RegionsClient":
        return cls(base_url=config.REGIONS_API_URL)

    async def close(self) -> None:
        await self._client.aclose()

    async def search_stations(self, *, q: str, limit: int = 20) -> list[dict]:
        response = await self._client.get("/stations/search", params={"q": q, "limit": limit})
        response.raise_for_status()
        return response.json()
