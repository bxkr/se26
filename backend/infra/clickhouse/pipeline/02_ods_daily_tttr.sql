-- Шаг 2: RAW → ODS · параметр :business_date
--
-- Разворачиваем payload_json из dwh.raw_daily_events в типизированные колонки.
-- Фильтруем по дате наблюдения из самого payload (а не ingested_at), чтобы
-- шаг был воспроизводим независимо от того, когда фактически был запущен RAW.
-- ON CONFLICT DO UPDATE — повторный запуск за тот же business_date просто
-- перезаписывает те же значения (идемпотентность).

INSERT INTO dwh.ods_daily_tttr (
    station_id, observation_date, temperature, temp_min, temp_max,
    precipitation_mm, business_date
)
SELECT
    station_id,
    (payload_json->>'observation_date')::date AS observation_date,
    (payload_json->>'avg_temp')::double precision AS temperature,
    (payload_json->>'min_temp')::double precision AS temp_min,
    (payload_json->>'max_temp')::double precision AS temp_max,
    (payload_json->>'precipitation')::double precision AS precipitation_mm,
    :business_date::date AS business_date
FROM dwh.raw_daily_events
WHERE (payload_json->>'observation_date')::date = :business_date::date
ON CONFLICT (station_id, observation_date) DO UPDATE SET
    temperature      = EXCLUDED.temperature,
    temp_min         = EXCLUDED.temp_min,
    temp_max         = EXCLUDED.temp_max,
    precipitation_mm = EXCLUDED.precipitation_mm,
    business_date    = EXCLUDED.business_date;
