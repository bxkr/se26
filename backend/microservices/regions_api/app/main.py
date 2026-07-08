from __future__ import annotations

import csv
import os
from collections import defaultdict

from fastapi import FastAPI, HTTPException

DATA_PATH = os.environ.get("STATIONS_CSV_PATH", "/app/data/stations_regions.csv")

app = FastAPI(title="regions_api")

region_to_stations: dict[str, list[str]] = defaultdict(list)
station_to_region: dict[str, str] = {}
station_to_coords: dict[str, tuple[float, float]] = {}


def load_data(path: str) -> None:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            wmo_index = (row.get("WMO_index") or "").strip()
            if not wmo_index:
                continue

            region_id = (row.get("region_id") or "").strip()
            if region_id:
                region_to_stations[region_id].append(wmo_index)
                station_to_region[wmo_index] = region_id

            lat, lng = (row.get("lat") or "").strip(), (row.get("lng") or "").strip()
            if lat and lng:
                try:
                    station_to_coords[wmo_index] = (float(lat), float(lng))
                except ValueError:
                    pass


load_data(DATA_PATH)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "stations_loaded": len(station_to_region) + len(station_to_coords)}


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
