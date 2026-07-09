// Hard bounds on the date-range pickers — keeps requests inside the window
// the pipeline can actually backfill without hammering Airflow (see
// ANALYTICS_MAX_REQUEST_DAYS on analytics_api for the day-count cap).
// historical_fetcher now sources "actual" data from Open-Meteo's Archive API
// (migrated 2026-07-08/09), which has real coverage far beyond the old dead
// historical-se26.bxkr.org source this cap used to be pinned to — but
// REQUEST_MAX_DATE still needs to stay a manually-set date, not "today",
// since the DM pipeline only has rows for dates it has actually ingested.
export const REQUEST_MIN_DATE = "2022-01-01";
export const REQUEST_MAX_DATE = "2026-06-30";

// Mirrors front_api's FRONT_API_MAX_REQUEST_RANGE_DAYS default (see
// backend/microservices/front_api/app/config.py) — keeps the picker from
// ever producing a range the API will reject with 400 VALIDATION_ERROR.
// Client-side clamp only; the API is still the source of truth.
export const MAX_REQUEST_RANGE_DAYS = 180;

// Pages default their date-range pickers to "last 30 days" — anchored to
// REQUEST_MAX_DATE rather than `new Date()` so the default stays valid even
// when the system clock is past REQUEST_MAX_DATE.
export const DEFAULT_RANGE_TO = REQUEST_MAX_DATE;
export const DEFAULT_RANGE_FROM = new Date(new Date(REQUEST_MAX_DATE).getTime() - 30 * 24 * 60 * 60 * 1000)
  .toISOString()
  .slice(0, 10);

// Explorer ("Регионы и станции") defaults to a fixed historical window
// instead of the rolling "last 30 days" the other pages use.
export const EXPLORER_DEFAULT_RANGE_FROM = "2024-10-15";
export const EXPLORER_DEFAULT_RANGE_TO = "2024-12-28";
export const EXPLORER_DEFAULT_REGION_ID = "44";
export const EXPLORER_DEFAULT_STATION = {
  wmoIndex: "26075",
  name: "Санкт-Петербург (Воейково) (РС)",
} as const;

export const DEMO_CREDENTIALS = {
  username: "demo",
  password: "demo12345",
};

export const POLL_INTERVAL_MS = 1500;
