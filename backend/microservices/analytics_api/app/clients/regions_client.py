from __future__ import annotations

import httpx

from app.config import config


class RegionNotFoundError(Exception):
    def __init__(self, region_id: str) -> None:
        self.region_id = region_id
        super().__init__(f"unknown region_id: {region_id}")


class RegionsClient:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)

    @classmethod
    def from_env(cls) -> "RegionsClient":
        return cls(base_url=config.REGIONS_API_URL)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_wmo_indexes_for_region(self, region_id: str) -> list[str]:
        response = await self._client.get(f"/regions/{region_id}/wmo-indexes")
        if response.status_code == 404:
            raise RegionNotFoundError(region_id)
        response.raise_for_status()
        return response.json()["wmo_indexes"]

    async def get_wmo_indexes_for_regions(self, region_ids: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for region_id in region_ids:
            for wmo_index in await self.get_wmo_indexes_for_region(region_id):
                if wmo_index not in seen:
                    seen.add(wmo_index)
                    result.append(wmo_index)
        return result

    async def get_names_for_wmo_indexes(self, wmo_indexes: list[str]) -> dict[str, str]:
        if not wmo_indexes:
            return {}
        response = await self._client.post("/wmo-indexes/names", json={"wmo_indexes": wmo_indexes})
        response.raise_for_status()
        return response.json()["names"]
