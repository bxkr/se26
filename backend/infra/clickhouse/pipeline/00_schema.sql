-- DDL схемы dwh (init_warehouse.py)

CREATE SCHEMA IF NOT EXISTS dwh;

CREATE TABLE IF NOT EXISTS dwh.dds_dim_station (
    station_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS dwh.raw_daily_events (
    event_id        TEXT PRIMARY KEY,
    station_id      TEXT NOT NULL,
    payload_json    JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS dwh.ods_daily_tttr (
    station_id        TEXT NOT NULL,
    observation_date  DATE NOT NULL,
    temperature       DOUBLE PRECISION,
    temp_min          DOUBLE PRECISION,
    temp_max          DOUBLE PRECISION,
    precipitation_mm  DOUBLE PRECISION,
    business_date     DATE NOT NULL,
    PRIMARY KEY (station_id, observation_date)
);

CREATE TABLE IF NOT EXISTS dwh.dm_fct_daily_weather (
    station_id        TEXT NOT NULL,
    day               DATE NOT NULL,
    temperature       DOUBLE PRECISION,
    temp_min          DOUBLE PRECISION,
    temp_max          DOUBLE PRECISION,
    precipitation_mm  DOUBLE PRECISION,
    PRIMARY KEY (station_id, day)
);

CREATE TABLE IF NOT EXISTS dwh.etl_state (
    pipeline_name TEXT NOT NULL,
    key           TEXT NOT NULL,
    value         TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (pipeline_name, key)
);

CREATE INDEX IF NOT EXISTS idx_ods_daily_tttr_business_date
    ON dwh.ods_daily_tttr (business_date);
CREATE INDEX IF NOT EXISTS idx_dm_fct_day ON dwh.dm_fct_daily_weather (day);
