-- Шаг 1: L6 → RAW · параметр :business_date
--
-- Источник (L6, operational): public.stations + public.weather_data
--   stations(id, wmo_index, name, country)
--   weather_data(id, station_id -> stations.id, observation_date,
--                quality_flag, min_temp, avg_temp, max_temp, precipitation)
--
-- event_id = weather_data.id (surrogate PK L6, стабилен между перезапусками
-- pipeline за один и тот же business_date -> ON CONFLICT DO NOTHING делает
-- шаг идемпотентным).

INSERT INTO dwh.raw_daily_events (event_id, station_id, payload_json, ingested_at)
SELECT
    wd.id::text AS event_id,
    s.wmo_index AS station_id,
    jsonb_build_object(
        'wmo_index', s.wmo_index,
        'name', s.name,
        'country', s.country,
        'observation_date', wd.observation_date,
        'quality_flag', wd.quality_flag,
        'min_temp', wd.min_temp,
        'avg_temp', wd.avg_temp,
        'max_temp', wd.max_temp,
        'precipitation', wd.precipitation
    ) AS payload_json,
    NOW() AS ingested_at
FROM public.weather_data wd
JOIN public.stations s ON s.id = wd.station_id
WHERE wd.observation_date = :business_date::date
ON CONFLICT (event_id) DO NOTHING;