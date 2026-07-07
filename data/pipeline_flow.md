# Сквозной поток данных: запрос → analytics_api → ответ

**Статус:** Vision / план (авторитетный источник — этот документ; код обязан подтягиваться к нему, не наоборот)
**Дата:** 07.07.2026

## Схема

Решено: клиент работает по **поллингу** (`202 Accepted` + `request_id`, затем `GET /requests/{id}`), а не держит HTTP-соединение открытым на всю глубину пайплайна. Состояние запроса хранится в `analytics_api` (таблица `request_status`, ключ — `trace_id` = `request_id`) и обновляется по мере прихода Kafka-событий, включая событие об ошибке `weather.pipeline.failed`, которое может прилететь с любого шага.

```
Клиент
  │  POST /weather?... (запрос данных)
  ▼
analytics_api
  │  данные уже есть в ClickHouse? ── да ──► читает ClickHouse ──► 200 с данными
  │  нет:
  │    - создаёт request_status(request_id=trace_id, status=PENDING)
  │    - publish weather.need_info {trace_id}
  │    - отвечает 202 {request_id, poll_url: /requests/{request_id}}
  ▼
Клиент опрашивает GET /requests/{request_id} до status ∈ {READY, FAILED}

────────────────────── дальше — цепочка событий, каждый шаг обновляет request_status по trace_id ──────────────────────

historical_fetcher / predict_fetcher (consumer weather.need_info)
  │  данных за период нет ──► publish weather.pipeline.failed {trace_id, stage: fetch}
  │  данные есть ──► кладут json в S3 (weather-raw) ──► publish weather.actual.raw.created {trace_id}
  ▼
etl_service (consumer weather.actual.raw.created)
  │  ошибка валидации / записи ──► publish weather.pipeline.failed {trace_id, stage: etl}
  │  успех ──► upsert в PostgreSQL (operational, weather_actual) ──► publish weather.clean.created {trace_id}
  ▼
dm_trigger (новый сервис, consumer weather.clean.created)
  │  вызывает Airflow REST API: POST /dags/{dag_id}/dagRuns  {conf: {trace_id, business_date, dataset_type}}
  │  вызов не прошёл ──► publish weather.pipeline.failed {trace_id, stage: dm_trigger}
  ▼
Airflow DAG (получает trace_id/dataset_type через dag_run.conf)
  │  SparkSubmitOperator: PySpark job, --dataset-type actual|forecast
  │    dataset_type=actual: читает weather_actual (JDBC) → пишет raw_weather_events/ods_daily_weather/dm_fct_daily_weather
  │    dataset_type=forecast: читает weather_forecast (JDBC, временный stand-in под predict_fetcher) → пишет raw_forecast_events/ods_daily_forecast/dm_fct_daily_forecast
  │    трансформация по спецификации infra/clickhouse/pipeline/{01,02,03}*.sql (RAW→ODS→DM — эталон/acceptance, не исполняется напрямую)
  │    после записи DM-слоя (в любой ветке) — пересчёт dm_fct_forecast_error:
  │      inner join dm_fct_daily_weather × dm_fct_daily_forecast по (wmo_index, day) для этого business_date,
  │      знаковая (forecast-actual) и абсолютная ошибка на каждую метрику; если второй стороны ещё нет — join пуст, пропуск (дозаполнится позже, порядок actual/forecast не важен)
  │  DAG упал (on_failure_callback) ──► publish weather.pipeline.failed {trace_id, stage: dm}
  │  успех ──► publish weather.dm.ready {trace_id, dataset_type}
  ▼
analytics_api (consumer weather.dm.ready И weather.pipeline.failed)
  │  READY: читает нужные данные из ClickHouse, кладёт в request_status, status=READY
  │  FAILED: request_status.status=FAILED + error_message (stage, reason)
  ▼
Клиент видит через GET /requests/{request_id}: {status: READY, data: …} либо {status: FAILED, error: …}
```

## Статус по шагам (относительно кода на 07.07.2026)

| # | Шаг | Статус |
|---|-----|--------|
| 1 | `analytics_api`: приём запроса, чтение из ClickHouse при кэш-хите | ❌ не реализовано (`app/main.py`, `app/api/routes.py` и весь модуль — пустые файлы-заглушки) |
| 2 | `analytics_api` → `weather.need_info` | ❌ не реализовано (нет kafka-продюсера в analytics_api) |
| 3 | `historical_fetcher`: consume `weather.need_info` → внешний API → S3 → `weather.actual.raw.created` | ✅ реализовано (`EventProcessor.java`) |
| 3b | `predict_fetcher` (аналог для прогнозов) | ❌ не создан (упоминается только в `data/structure.txt`) |
| 4 | `etl_service`: consume `weather.actual.raw.created` → S3 → normalize/validate → upsert Postgres | ✅ реализовано (`raw_event_handler.py`, `writer.py`) |
| 4b | `etl_service` → publish `weather.clean.created` | ❌ не реализовано (ответственность другой части команды) — `weather.clean.created` существует как контракт, эмулируется вручную для сквозного теста |
| 5 | `dm_trigger`: consume `weather.clean.created` → триггер Airflow DAG `dm_pipeline` через REST API, пробрасывая `dataset_type` | ✅ реализовано и задеплоено (`backend/microservices/dm_trigger/`), задеплоено в `dm-pipeline` namespace на k8s |
| 6 | Airflow DAG + PySpark job, `dataset_type`-aware (`weather_actual`/`weather_forecast` → ClickHouse RAW/ODS/DM, lean: `airflow standalone` + `local[2]`) | ✅ реализовано и задеплоено (`backend/microservices/dm_pipeline/`); реальная ClickHouse-схема — `backend/infra/clickhouse/schema.sql` (`pipeline/*.sql` остаются эталоном/спецификацией, не исполняются) |
| 6b | Витрина `dm_fct_forecast_error` (join `dm_fct_daily_weather`×`dm_fct_daily_forecast` по `(wmo_index, day)`, знаковая+абсолютная ошибка на метрику) | ✅ реализовано (пересчёт — часть той же Spark-джобы, после каждой DM-записи) |
| 7 | публикация `weather.dm.ready` по завершении DAG | ✅ реализовано (`weather.dm.ready` + `weather.pipeline.failed` в `contracts/`), сквозной прогон подтверждён (см. ниже) |
| 8 | `analytics_api`: consume `weather.dm.ready`, забрать данные из ClickHouse, ответить клиенту | ❌ не реализовано (`analytics_api` — ответственность другой части команды) |
| 3c | `predict_fetcher`: consume `weather.need_info` → внешний прогнозный API → S3 → `weather.actual.raw.created`-аналог | ❌ не создан; когда появится — достаточно писать в `weather_forecast` (Postgres, временный stand-in) и публиковать `weather.clean.created{dataset_type: "forecast"}`, остальное (шаги 5–7) уже готово принять эту ветку |

### Сквозная проверка шагов 5–7 (07.07.2026, вручную эмулированный `weather.clean.created`)

Задеплоено на k8s (namespace `dm-pipeline`, кластер `cathalm54htunnn6ugcm`): `kafka`, `postgres` (стенд с схемой `weather_actual`), `clickhouse`, `airflow` (+ своя metadata-postgres), `dm-trigger`. Helm-чарты — `backend/deploy/helm/`.

Прогнано и подтверждено:
- тестовая строка в `weather_actual` → `weather.clean.created` → `dm_trigger` триггерит DAG `dm_pipeline` → Spark читает Postgres, пишет RAW/ODS/DM в ClickHouse → `weather.dm.ready` с корректным `trace_id`/`record_count`;
- идемпотентность: повторный прогон за тот же `business_date` не дублирует строку в `dm_fct_daily_weather` (`ReplacingMergeTree` + `FINAL`);
- путь ошибки: некорректное событие (без `trace_id`/`observation_date`) → `dm_trigger` публикует `weather.pipeline.failed{stage: dm_trigger}`; падение Spark-таска в DAG → `on_failure_callback` публикует `weather.pipeline.failed{stage: dm}`.

### Сквозная проверка прогнозной ветки + витрины ошибки (07.07.2026)

Добавлены и задеплоены (wipe+reinstall `postgres`/`clickhouse`-чартов под новую схему): таблица `weather_forecast` в Postgres, таблицы `raw_forecast_events`/`ods_daily_forecast`/`dm_fct_daily_forecast` и витрина `dm_fct_forecast_error` в ClickHouse; `dm_trigger`/DAG/Spark-джоба обновлены и передеплоены (`docker buildx build --platform linux/amd64 ... --push` + `helm upgrade` — понадобилось также включить `pullPolicy: Always` в `dm-trigger`-чарте, он был `IfNotPresent` и не подхватывал новый образ под тем же тегом `:latest`, тот же класс проблемы, что уже фиксировался для `airflow`-чарта).

Прогнано и подтверждено на той же станции/дате (`wmo_index=20674`, `1960-01-01`):
- `weather.clean.created{dataset_type: "actual"}` → `dm_fct_daily_weather` заполнилась, `dm_fct_forecast_error` пуста (второй стороны ещё нет);
- следом `weather.clean.created{dataset_type: "forecast"}` (та же дата/станция, намеренно другие значения метрик) → `dm_fct_daily_forecast` заполнилась, `dm_fct_forecast_error` посчиталась с корректными знаковыми (`temperature_error=1.9`, `temp_min_error=2.1`, `temp_max_error=1.9`, `precipitation_mm_error=0.5`) и абсолютными ошибками, `actual_trace_id`/`forecast_trace_id` указывают на исходные события;
- идемпотентность: повторная публикация `weather.clean.created{dataset_type: "forecast"}` за тот же `business_date` (новый `event_id`) не задублировала ни `dm_fct_daily_forecast`, ни `dm_fct_forecast_error` (`ReplacingMergeTree` + `FINAL`).

Нод-пул кластера расширен до 4vCPU/8GB под эту нагрузку (`terraform/bootstrap/kubernetes-nodegroup.tf`, применено).

**Вывод:** план в целом рабочий и логически связный (событийная цепочка с S3 как промежуточным хранилищем и Kafka как шиной уже наполовину реализована и работает для веток 3–4). Разрыв — всё, что после `weather.clean.created`: там нет ни одного компонента, только SQL-файлы витрины.

## Принятые решения

1. **Клиент ↔ analytics_api: поллинг, не held-open HTTP.** `analytics_api` на cache-miss сразу отвечает `202 Accepted {request_id, poll_url}` и не блокирует поток/соединение на всю глубину пайплайна. Прогресс отслеживается через таблицу `request_status` (PostgreSQL или отдельная схема в `analytics_api`), ключ — `trace_id`; каждый Kafka-consumer в `analytics_api` (`weather.dm.ready`, `weather.pipeline.failed`) только обновляет строку по `trace_id`, GET `/requests/{id}` её читает. WebSocket/SSE как более отзывчивая альтернатива поллингу — не в скоупе сейчас, можно добавить позже без смены модели данных.
2. **Триггер Airflow — отдельный сервис `dm_trigger`.** Consumer `weather.clean.created`, единственная обязанность — вызвать Airflow REST API `POST /dags/{dag_id}/dagRuns` с `conf: {trace_id, business_date}` и обработать ответ (retry / `weather.pipeline.failed` при неуспехе). Не часть `etl_service` и не часть `analytics_api` — чтобы Airflow-специфичный код (auth, retry-политика конкретно под Airflow API) не тёк в бизнес-сервисы.
3. **Spark делает трансформацию; SQL-файлы `infra/clickhouse/pipeline/*.sql` — эталон/acceptance-спецификация, не исполняемый пайплайн.** PySpark job (запускается `SparkSubmitOperator` из Airflow DAG) сам читает Postgres по JDBC, трансформирует RAW→ODS→DM и пишет в ClickHouse. `01_raw_load.sql`…`03_dm_fct_daily_weather.sql` остаются как документированная спецификация того, что каждый слой обязан содержать (по ним можно писать data-quality тесты/сверку результата Spark-джобы), но в проде их текст напрямую не гоняется.
4. **Единый контракт ошибки `weather.pipeline.failed`.** Публикуется любым шагом на любой сбой: `{event_id, trace_id, event_type: "weather.pipeline.failed", stage: fetch|etl|dm_trigger|dm, source_name, reason, details, schema_version, created_at}`. В частности, `historical_fetcher` должен публиковать его вместо тихого `ack.acknowledge()` в случае `s3Keys.isEmpty()` (`EventProcessor.java:147`) — «нет данных за период» это тоже терминальный исход для `analytics_api`, а не просто лог. `analytics_api` консьюмит этот topic наравне с `weather.dm.ready` и переводит `request_status` в `FAILED` с `stage`/`reason` от источника. Таймаут на стороне `analytics_api` (на случай, если событие само потеряется) — отдельная защита, не исключает основной канал через событие.
5. **Прогнозная ветка переиспользует существующий контракт/DAG/топики, без дублирования инфраструктуры.** Поле `dataset_type` (`"actual"`|`"forecast"`), уже присутствовавшее в `weather.clean.created`/`weather.dm.ready`, стало реальным дискриминатором: `dm_trigger` пробрасывает его в `dag_run.conf`, DAG передаёт Spark-джобе через `--dataset-type`, джоба по нему выбирает источник в Postgres (`weather_actual`/`weather_forecast`) и целевые ClickHouse-таблицы (`*_weather`/`*_forecast`). Один DAG, один Airflow-эндпоинт, один набор Kafka-топиков — вместо параллельной инфраструктуры под прогнозы. Пока `predict_fetcher` не построен, `weather_forecast` в Postgres — временная ручная stand-in таблица (той же формы, что `weather_actual`) для сквозного тестирования. Ошибка прогноза в `dm_fct_forecast_error` считается и знаково (`forecast - actual`, показывает смещение), и абсолютно (`|forecast - actual|`, для агрегатной точности вроде MAE) — по каждой метрике (`temperature`, `temp_min`, `temp_max`, `precipitation_mm`); пересчитывается после каждой DM-записи (в любой из двух веток) через `inner join` `dm_fct_daily_weather`×`dm_fct_daily_forecast` по `(wmo_index, day)` — если второй стороны ещё нет, join пуст и ничего не пишется, витрина дозаполнится независимо от порядка прихода actual/forecast.

## Что нужно завести дополнительно (относительно текущего кода)

Сделано (07.07.2026, задеплоено на k8s namespace `dm-pipeline`):
- ~~Новый topic `weather.dm.ready` + `weather.pipeline.failed`~~ — в `contracts/topics.json` и `contracts/events/`.
- ~~Новый микросервис `dm_trigger`~~ — `backend/microservices/dm_trigger/`.
- ~~Airflow + Spark~~ — `backend/microservices/dm_pipeline/` (lean: `airflow standalone`, LocalExecutor, PySpark `local[2]` в том же поде), Helm-чарты в `backend/deploy/helm/{kafka,postgres,clickhouse,airflow,dm-trigger}`.
- ~~PySpark job~~ — `spark_jobs/postgres_to_clickhouse.py`, реальная ClickHouse-схема `infra/clickhouse/schema.sql`.
- ~~Прогнозная ветка (`dataset_type`-ветвление в `dm_trigger`/DAG/Spark, таблицы `raw_forecast_events`/`ods_daily_forecast`/`dm_fct_daily_forecast`, витрина ошибки `dm_fct_forecast_error`, временная Postgres-таблица `weather_forecast`)~~ — `backend/infra/postgres/init.sql`, `backend/infra/clickhouse/schema.sql`.

Ещё не сделано:
- Kafka-продюсер в `etl_service` + вызов после успешного `writer.write(...)` → публикация `weather.clean.created` (шаг 4b) — ответственность другой части команды.
- Реализация `analytics_api` целиком: HTTP-роуты (`POST /weather`, `GET /requests/{id}`), таблица/хранилище `request_status`, kafka-продюсер (`weather.need_info`) и consumer (`weather.dm.ready` + `weather.pipeline.failed`), ClickHouse-клиент.
- Правка `historical_fetcher`: публиковать `weather.pipeline.failed` вместо молчаливого `ack.acknowledge()` при `s3Keys.isEmpty()`.
- `predict_fetcher` — если он всё ещё в плане (см. `data/structure.txt`), сейчас не создан, аналог `historical_fetcher` для прогнозов; должен следовать тому же контракту ошибок. Downstream (шаги 5–7) уже готов принять его вывод: писать в `weather_forecast` (Postgres, сейчас — временный ручной stand-in, см. `infra/postgres/init.sql`) и публиковать `weather.clean.created{dataset_type: "forecast"}` — дальше `dm_trigger`/DAG/Spark сами доведут до `dm_fct_daily_forecast`/`dm_fct_forecast_error`/`weather.dm.ready`.
- Деплой существующих микросервисов (`etl_service`, `historical_fetcher`, будущий `analytics_api`) на тот же k8s-кластер — сейчас они есть только в локальном `docker-compose`, `dm-pipeline`-стенд использует отдельный `postgres`-чарт как временную замену операционной БД (см. `backend/deploy/helm/postgres/values.yaml`).
- `.sourcecraft/ci.yaml` для `se26` — сейчас всё собрано/задеплоено вручную (`docker build/push` + `helm upgrade --install`).