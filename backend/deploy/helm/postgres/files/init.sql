BEGIN;

CREATE TABLE IF NOT EXISTS weather_actual (
    source_name TEXT NOT NULL,
    observation_date DATE NOT NULL,
    wmo_index TEXT NOT NULL,
    station_name TEXT NOT NULL,
    country TEXT NOT NULL,
    min_temp DOUBLE PRECISION NULL,
    avg_temp DOUBLE PRECISION NULL,
    max_temp DOUBLE PRECISION NULL,
    precipitation DOUBLE PRECISION NULL,
    raw_bucket TEXT NOT NULL,
    raw_object_key TEXT NOT NULL,
    event_id UUID NOT NULL,
    trace_id UUID NOT NULL,
    event_created_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_weather_actual
        PRIMARY KEY (source_name, observation_date, wmo_index),

    CONSTRAINT chk_weather_actual_source_name_not_blank
        CHECK (btrim(source_name) <> ''),

    CONSTRAINT chk_weather_actual_wmo_index_not_blank
        CHECK (btrim(wmo_index) <> ''),

    CONSTRAINT chk_weather_actual_station_name_not_blank
        CHECK (btrim(station_name) <> ''),

    CONSTRAINT chk_weather_actual_country_not_blank
        CHECK (btrim(country) <> ''),

    CONSTRAINT chk_weather_actual_raw_bucket_not_blank
        CHECK (btrim(raw_bucket) <> ''),

    CONSTRAINT chk_weather_actual_raw_object_key_not_blank
        CHECK (btrim(raw_object_key) <> '')
);

CREATE INDEX IF NOT EXISTS idx_weather_actual_observation_date
    ON weather_actual (observation_date);

CREATE INDEX IF NOT EXISTS idx_weather_actual_wmo_index
    ON weather_actual (wmo_index);

CREATE INDEX IF NOT EXISTS idx_weather_actual_event_id
    ON weather_actual (event_id);

CREATE INDEX IF NOT EXISTS idx_weather_actual_trace_id
    ON weather_actual (trace_id);

CREATE INDEX IF NOT EXISTS idx_weather_actual_raw_object_key
    ON weather_actual (raw_object_key);

CREATE INDEX IF NOT EXISTS idx_weather_actual_source_date
    ON weather_actual (source_name, observation_date);

COMMENT ON TABLE weather_actual IS
'Normalized daily weather facts loaded by etl_service from historical daily raw files in S3.';

COMMENT ON COLUMN weather_actual.source_name IS
'Producer/source of raw data, e.g. historical_fetcher.';

COMMENT ON COLUMN weather_actual.observation_date IS
'Observation day taken from daily raw file body.date and object key actual/date=YYYY-MM-DD.json.';

COMMENT ON COLUMN weather_actual.raw_bucket IS
'S3 bucket containing canonical daily raw files.';

COMMENT ON COLUMN weather_actual.raw_object_key IS
'Canonical S3 object key, e.g. actual/date=1960-01-01.json.';

COMMENT ON COLUMN weather_actual.event_id IS
'Kafka event_id of weather.actual.raw.created event used for this upsert.';

COMMENT ON COLUMN weather_actual.trace_id IS
'Trace identifier propagated from source event.';

COMMENT ON COLUMN weather_actual.event_created_at IS
'Timestamp from Kafka event payload, not DB ingestion time.';

COMMENT ON COLUMN weather_actual.ingested_at IS
'Timestamp when row was inserted/updated in Postgres.';

COMMIT;