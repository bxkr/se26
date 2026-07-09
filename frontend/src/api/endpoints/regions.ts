import { apiGet } from "../client";

export interface StationSearchResult {
  wmo_index: string;
  name: string;
}

export function searchStations(q: string): Promise<StationSearchResult[]> {
  return apiGet(`/stations/search?q=${encodeURIComponent(q)}&limit=20`);
}
