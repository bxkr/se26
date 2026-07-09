from __future__ import annotations

import csv
import os
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DATA_PATH = os.environ.get("STATIONS_CSV_PATH", "/app/data/stations_regions_v2.csv")

app = FastAPI(title="regions_api")

region_to_stations: dict[str, list[str]] = defaultdict(list)
station_to_region: dict[str, str] = {}
station_to_coords: dict[str, tuple[float, float]] = {}
station_to_name: dict[str, str] = {}


def load_data(path: str) -> None:
    skipped_no_id = 0
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            wmo_index = (row.get("WMO_index") or "").strip()
            if not wmo_index:
                # A handful of rows (radar stations) carry no unique station
                # identifier at all in stations_regions_v2.csv - nothing to
                # key them by under the wmo_index-keyed endpoints below.
                skipped_no_id += 1
                continue

            name = (row.get("Station") or "").strip()
            if name:
                station_to_name[wmo_index] = name

            region_id = (row.get("Region") or "").strip()
            if region_id:
                region_to_stations[region_id].append(wmo_index)
                station_to_region[wmo_index] = region_id

            lat, lng = (row.get("Latitude") or "").strip(), (row.get("Longitude") or "").strip()
            if lat and lng:
                try:
                    station_to_coords[wmo_index] = (float(lat), float(lng))
                except ValueError:
                    pass

    if skipped_no_id:
        print(f"load_data: skipped {skipped_no_id} rows with no WMO_index (no unique station id)")


load_data(DATA_PATH)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "stations_loaded": len(station_to_region) + len(station_to_coords),
        "stations_with_name": len(station_to_name),
    }


@app.get("/regions/{region_id}/wmo-indexes")
def get_region_wmo_indexes(region_id: str) -> dict:
    stations = region_to_stations.get(region_id)
    if not stations:
        raise HTTPException(status_code=404, detail=f"unknown region_id: {region_id}")
    return {"region_id": region_id, "wmo_indexes": stations}


@app.get("/wmo-indexes/{wmo_index}/region")
def get_wmo_index_region(wmo_index: str) -> dict:
    region_id = station_to_region.get(wmo_index)
    if region_id is None:
        raise HTTPException(status_code=404, detail=f"unknown wmo_index (or no region): {wmo_index}")
    return {"wmo_index": wmo_index, "region_id": region_id}


@app.get("/wmo-indexes/{wmo_index}/coordinates")
def get_wmo_index_coordinates(wmo_index: str) -> dict:
    coords = station_to_coords.get(wmo_index)
    if coords is None:
        raise HTTPException(status_code=404, detail=f"unknown wmo_index (or no coordinates): {wmo_index}")
    return {"wmo_index": wmo_index, "lat": coords[0], "lng": coords[1]}


@app.get("/wmo-indexes/{wmo_index}/name")
def get_wmo_index_name(wmo_index: str) -> dict:
    name = station_to_name.get(wmo_index)
    if name is None:
        raise HTTPException(status_code=404, detail=f"unknown wmo_index (or no name): {wmo_index}")
    return {"wmo_index": wmo_index, "name": name}


@app.get("/wmo-indexes/{wmo_index}")
def get_wmo_index_details(wmo_index: str) -> dict:
    if (
        wmo_index not in station_to_name
        and wmo_index not in station_to_region
        and wmo_index not in station_to_coords
    ):
        raise HTTPException(status_code=404, detail=f"unknown wmo_index: {wmo_index}")

    coords = station_to_coords.get(wmo_index)
    return {
        "wmo_index": wmo_index,
        "name": station_to_name.get(wmo_index),
        "region_id": station_to_region.get(wmo_index),
        "lat": coords[0] if coords else None,
        "lng": coords[1] if coords else None,
    }


class WmoIndexNamesRequest(BaseModel):
    wmo_indexes: list[str]


@app.post("/wmo-indexes/names")
def get_wmo_index_names(payload: WmoIndexNamesRequest) -> dict:
    names = {wmo: station_to_name[wmo] for wmo in payload.wmo_indexes if wmo in station_to_name}
    return {"names": names}


@app.get("/stations/search")
def search_stations(q: str = "", limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 50))
    query = q.strip().lower()
    if not query:
        return []

    matches: list[dict] = []
    for wmo_index, name in station_to_name.items():
        if query in name.lower() or wmo_index.startswith(query):
            matches.append({"wmo_index": wmo_index, "name": name})
            if len(matches) >= limit:
                break
    return matches
