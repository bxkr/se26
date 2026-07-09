BEGIN;

-- weather_actual / weather_forecast used to live here as a stand-in for
-- historical weather data, loaded by etl_service via Postgres JDBC. Both the
-- table and etl_service are gone now — Spark reads raw JSON directly from S3
-- (see data/pipeline_flow.md, "Принятые решения"). This database stays
-- alive for future front_api user data; no weather-data tables here anymore.

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('user', 'admin')),
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
