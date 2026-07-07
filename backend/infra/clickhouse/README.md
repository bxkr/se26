# ClickHouse (DM-слой)

**`schema.sql`** — реальная, исполняемая ClickHouse DDL (RAW/ODS/DM), которую создаёт/наполняет PySpark-джоба `backend/microservices/dm_pipeline/spark_jobs/postgres_to_clickhouse.py`. Источник данных — PostgreSQL `weather_actual` (`infra/postgres/init.sql`), не `pipeline/*.sql`.

**`pipeline/*.sql`** — Postgres-диалект, унаследован из семинарской лабы (sem8/L8) и читает несуществующие в этом проекте таблицы `public.stations`/`public.weather_data`. Это **не исполняемый в проде код**, а эталон/acceptance-спецификация слоёв RAW→ODS→DM: по нему можно проверять, что результат Spark-джобы (`schema.sql`) семантически покрывает те же поля и трансформации (агрегация температур/осадков по дню, идемпотентность повторного прогона за тот же `business_date`). Подробности — `data/pipeline_flow.md`, раздел «Принятые решения», п.3.

**`init.sql`** — плейсхолдер (`SELECT 1;`), исторический артефакт, не используется.
