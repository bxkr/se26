-- Шаг 3: ODS → DM · параметр :business_date
--
-- Delete-Insert за день: витрина не хранит now()/ingested_at, поэтому
-- переигровка business_date просто выкидывает старый снапшот дня и строит
-- заново из ODS — идемпотентно и без накопления дублей.
-- Оба стейтмента выполняются в одной транзакции (run_pipeline.py коммитит
-- после всего файла), так что промежуточного состояния "день удалён,
-- но ещё не перезаполнен" снаружи не видно.

DELETE FROM dwh.dm_fct_daily_weather
WHERE day = :business_date::date;

INSERT INTO dwh.dm_fct_daily_weather (
    station_id, day, temperature, temp_min, temp_max, precipitation_mm
)
SELECT
    station_id,
    observation_date AS day,
    temperature,
    temp_min,
    temp_max,
    precipitation_mm
FROM dwh.ods_daily_tttr
WHERE observation_date = :business_date::date;
