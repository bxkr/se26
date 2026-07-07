-- Historical ETL seed is intentionally empty.
-- Canonical daily raw storage:
--   bucket: weather-raw
--   object key format: actual/date=YYYY-MM-DD.json
--   event type / topic: weather.actual.raw.created
--
-- This file remains as a no-op so docker init pipelines do not fail.

SELECT 'postgres seed: no-op for historical ETL' AS message;