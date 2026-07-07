# dm_pipeline

Airflow (`airflow standalone`, LocalExecutor, single pod) + PySpark job (`local[*]`, no separate Spark cluster — lean profile, см. `data/pipeline_flow.md`). DAG `dm_pipeline` не имеет расписания — триггерится только `dm_trigger` через `POST /api/v1/dags/dm_pipeline/dagRuns`.

## Env vars

| Var | Использует | Назначение |
|---|---|---|
| `POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` | `spark_jobs/postgres_to_clickhouse.py` | источник — `weather_actual` |
| `CLICKHOUSE_HOST`/`CLICKHOUSE_HTTP_PORT`/`CLICKHOUSE_DB`/`CLICKHOUSE_USER`/`CLICKHOUSE_PASSWORD` | `spark_jobs/postgres_to_clickhouse.py` | цель — `raw_weather_events`/`ods_daily_weather`/`dm_fct_daily_weather` |
| `KAFKA_BOOTSTRAP_SERVERS` | `common/kafka_events.py` (вызывается из `dags/dm_pipeline_dag.py`) | публикация `weather.dm.ready`/`weather.pipeline.failed` |
| `AIRFLOW__CORE__EXECUTOR`, `AIRFLOW__CORE__LOAD_EXAMPLES` | Airflow | заданы в Dockerfile, не переопределять без причины |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | Airflow | метаданные Airflow (отдельный Postgres, см. Helm-чарт `airflow`) — задаётся через Helm values/Secret, не хардкодится в образе |
| Basic Auth пользователь для REST API | `dm_trigger` (`AIRFLOW_API_USERNAME`/`AIRFLOW_API_PASSWORD`) | создаётся в Helm-чарте `airflow` (init) |
