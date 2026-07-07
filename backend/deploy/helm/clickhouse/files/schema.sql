-- Настоящая схема ClickHouse (DM-слой сквозного пайплайна).
--
-- В отличие от pipeline/*.sql (Postgres-диалект, читают несуществующие в
-- этом проекте public.stations/public.weather_data — эталон RAW→ODS→DM из
-- лабы sem8, не исполняемый код) эти таблицы — реальная цель PySpark-джобы
-- (backend/microservices/dm_pipeline/spark_jobs/postgres_to_clickhouse.py),
-- источник данных — PostgreSQL-таблица weather_actual, которую пишет
-- etl_service (infra/postgres/init.sql).
--
-- Идемпотентность через ReplacingMergeTree(ingested_at) вместо
-- Postgres-паттерна DELETE+INSERT из pipeline/03_dm_fct_daily_weather.sql:
-- повторный прогон DAG за тот же business_date просто вставляет строки с
-- более свежим ingested_at, старая версия схлопывается фоновым merge'ем;
-- для гарантированно дедуплицированного чтения используйте FINAL
-- (см. вьюхи *_current в конце файла).

CREATE DATABASE IF NOT EXISTS weather;

-- RAW: построчное зеркало weather_actual для аудита/лога того, что видела
-- Spark-джоба на входе (полезно для отладки расхождений ODS/DM).
CREATE TABLE IF NOT EXISTS weather.raw_weather_events
(
    source_name       String,
    observation_date  Date32,
    wmo_index         String,
    station_name      String,
    country           String,
    min_temp          Nullable(Float64),
    avg_temp          Nullable(Float64),
    max_temp          Nullable(Float64),
    precipitation     Nullable(Float64),
    raw_bucket        String,
    raw_object_key    String,
    event_id          UUID,
    trace_id          UUID,
    event_created_at  DateTime,
    ingested_at       DateTime
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(observation_date)
ORDER BY (source_name, observation_date, wmo_index);

-- ODS: типизированный дневной срез по станции (семантика
-- pipeline/02_ods_daily_tttr.sql, источник колонок — weather_actual).
CREATE TABLE IF NOT EXISTS weather.ods_daily_weather
(
    wmo_index          String,
    station_name       String,
    country            String,
    observation_date   Date32,
    temperature        Nullable(Float64),  -- weather_actual.avg_temp
    temp_min           Nullable(Float64),  -- weather_actual.min_temp
    temp_max           Nullable(Float64),  -- weather_actual.max_temp
    precipitation_mm   Nullable(Float64),  -- weather_actual.precipitation
    trace_id           UUID,
    ingested_at        DateTime
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(observation_date)
ORDER BY (wmo_index, observation_date);

-- DM: витрина (семантика pipeline/03_dm_fct_daily_weather.sql), читает
-- analytics_api.
CREATE TABLE IF NOT EXISTS weather.dm_fct_daily_weather
(
    wmo_index          String,
    day                Date32,
    temperature        Nullable(Float64),
    temp_min           Nullable(Float64),
    temp_max           Nullable(Float64),
    precipitation_mm   Nullable(Float64),
    trace_id           UUID,
    ingested_at        DateTime
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(day)
ORDER BY (wmo_index, day);

-- Date32, не Date: исторические наблюдения уходят к 1960 году, а ClickHouse
-- Date хранит только дни с 1970-01-01 (2 байта, диапазон 0..65535).

-- Дедуплицированные вьюхи для чтения без ручного FINAL в каждом запросе.
CREATE VIEW IF NOT EXISTS weather.ods_daily_weather_current AS
SELECT * FROM weather.ods_daily_weather FINAL;

CREATE VIEW IF NOT EXISTS weather.dm_fct_daily_weather_current AS
SELECT * FROM weather.dm_fct_daily_weather FINAL;
