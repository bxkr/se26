# Сквозной поток данных: запрос → analytics_api → ответ

**Статус:** Vision / план (авторитетный источник — этот документ; код обязан подтягиваться к нему, не наоборот)
**Дата:** 08.07.2026

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

historical_fetcher / ForecastFetcher (consumer weather.need_info)
  │  данных за период нет ──► publish weather.pipeline.failed {trace_id, stage: fetch}
  │  данные есть ──► кладут json в S3 (managed Yandex Object Storage, bucket weather-raw,
  │                    actual/date=YYYY-MM-DD.json | forecast/date=YYYY-MM-DD.json)
  │                 ──► publish weather.actual.raw.created | weather.forecast.raw.created
  │                    {trace_id, event_id, source_name, bucket, object_keys[], date_from, date_to, created_at}
  ▼
dm_trigger (consumer ОБОИХ топиков — weather.actual.raw.created И weather.forecast.raw.created)
  │  dataset_type определяется топиком-источником (actual|forecast), не отдельным полем
  │  один манифест (может покрывать несколько дат, date_from..date_to) — ОДИН вызов Airflow REST API:
  │    POST /dags/{dag_id}/dagRuns
  │    {conf: {trace_id, date_from, date_to, dataset_type, bucket, source_name, event_id, event_created_at}}
  │    (не по одному DAG-рану на дату — см. «Батчинг dm_pipeline» ниже)
  │  вызов не прошёл / событие некорректно ──► publish weather.pipeline.failed {trace_id, stage: dm_trigger}
  ▼
Airflow DAG dm_pipeline (получает всё через dag_run.conf)
  │  BashOperator: spark-submit spark_jobs/s3_to_clickhouse.py --dataset-type actual|forecast --bucket ... --date-from ... --date-to ...
  │    сам строит список S3-ключей на каждый день диапазона (детерминированно из dataset_type: {prefix}/date=<day>.json)
  │    и читает их одним batch-чтением (один JSON-файл на день {date, stations:[...]}) — Postgres в этом пути больше нет
  │    dataset_type=actual: пишет raw_weather_events/ods_daily_weather/dm_fct_daily_weather
  │    dataset_type=forecast: пишет raw_forecast_events/ods_daily_forecast/dm_fct_daily_forecast
  │    трансформация по спецификации infra/clickhouse/pipeline/{01,02,03}*.sql (RAW→ODS→DM — эталон/acceptance, не исполняется напрямую)
  │    после записи DM-слоя (в любой ветке) — пересчёт dm_fct_forecast_error:
  │      inner join dm_fct_daily_weather × dm_fct_daily_forecast по (wmo_index, day) для каждого дня диапазона [date_from, date_to],
  │      знаковая (forecast-actual) и абсолютная ошибка на каждую метрику; если второй стороны ещё нет для какого-то дня — этот день просто отсутствует в join'е (дозаполнится позже, порядок actual/forecast не важен)
  │  DAG упал (on_failure_callback) ──► publish weather.pipeline.failed {trace_id, stage: dm}
  │  успех ──► publish weather.dm.ready {trace_id, dataset_type, date_from, date_to}
  ▼
analytics_api (consumer weather.dm.ready И weather.pipeline.failed)
  │  READY: читает нужные данные из ClickHouse, кладёт в request_status, status=READY
  │  FAILED: request_status.status=FAILED + error_message (stage, reason)
  ▼
Клиент видит через GET /requests/{request_id}: {status: READY, data: …} либо {status: FAILED, error: …}
```

`etl_service` из потока удалён — данные больше не проходят через Postgres, Spark читает сырой JSON напрямую из S3 (см. «Принятые решения», п.6). `weather.clean.created` — **retired**, ничего его больше не публикует и не потребляет.

## Статус по шагам (относительно кода на 08.07.2026)

| # | Шаг | Статус |
|---|-----|--------|
| 1 | `analytics_api`: приём запроса, чтение из ClickHouse при кэш-хите | ❌ не реализовано (`app/main.py`, `app/api/routes.py` и весь модуль — пустые файлы-заглушки) |
| 2 | `analytics_api` → `weather.need_info` | ❌ не реализовано (нет kafka-продюсера в analytics_api) |
| 3 | `historical_fetcher`: consume `weather.need_info` → внешний API → S3 → `weather.actual.raw.created` | ✅ реализовано (`EventProcessor.java`) |
| 3b | `ForecastFetcher` (аналог для прогнозов, пишет в S3 `forecast/date=...json` + `weather.forecast.raw.created`) | ✅ реализовано (`EventProcessor.java`, `source_name: "forecast_fetcher"`) |
| 4 | `etl_service`: consume `weather.actual.raw.created` → S3 → normalize/validate → upsert Postgres | 🗑️ удалён — Postgres выведен из пути погодных данных, Spark читает S3 напрямую (см. п.6 «Принятых решений») |
| 5 | `dm_trigger`: consume `weather.actual.raw.created` И `weather.forecast.raw.created` напрямую → триггер Airflow DAG `dm_pipeline` через REST API, один DAG-ран на манифест (весь `date_from..date_to`, не по дате) | ✅ реализовано (`backend/microservices/dm_trigger/`), задеплоено в `dm-pipeline` namespace на k8s |
| 6 | Airflow DAG + PySpark job, `dataset_type`-aware, читает raw JSON напрямую из S3 (`s3a://`) → ClickHouse RAW/ODS/DM (lean: `airflow standalone` + `local[2]`) | ✅ реализовано (`backend/microservices/dm_pipeline/`, `spark_jobs/s3_to_clickhouse.py`); реальная ClickHouse-схема — `backend/infra/clickhouse/schema.sql` (`pipeline/*.sql` остаются эталоном/спецификацией, не исполняются) |
| 6b | Витрина `dm_fct_forecast_error` (join `dm_fct_daily_weather`×`dm_fct_daily_forecast` по `(wmo_index, day)`, знаковая+абсолютная ошибка на метрику) | ✅ реализовано (пересчёт — часть той же Spark-джобы, после каждой DM-записи); работает поверх ClickHouse, источник данных (S3 vs было Postgres) для неё не важен |
| 7 | публикация `weather.dm.ready` по завершении DAG | ✅ реализовано (`weather.dm.ready` + `weather.pipeline.failed` в `contracts/`) |
| 8 | `analytics_api`: consume `weather.dm.ready`, забрать данные из ClickHouse, ответить клиенту | ❌ не реализовано (`analytics_api` — ответственность другой части команды) |

### Миграция на S3-прямой источник данных (08.07.2026)

`etl_service` удалён целиком (`backend/microservices/etl_service/` больше нет), вместе с ним из активного потока выведен контракт `weather.clean.created`. `dm_trigger` теперь подписан напрямую на `weather.actual.raw.created`/`weather.forecast.raw.created` — те же манифест-события, что раньше потреблял `etl_service`; `dataset_type` определяется по топику, а не по полю в событии. Одно манифест-событие может содержать несколько `object_keys` (несколько дат) — `dm_trigger` триггерит по одному `DagRun` на каждую дату.

Spark-джоба (`postgres_to_clickhouse.py` → `s3_to_clickhouse.py`) больше не читает Postgres по JDBC — читает сырой daily JSON прямо из S3 через Hadoop S3A-коннектор (`spark.read.json("s3a://bucket/object_key")`), разворачивает `stations[]`, дальше ODS/DM-маппинг и пересчёт витрины ошибки не изменились.

Боевой бакет — **managed Yandex Object Storage** (не MinIO в кластере), провижинится Terraform'ом (`yandex-cloud-sample/terraform/stage-1/object_storage.tf`): сервис-аккаунт со статическим ключом (WIF для Hadoop S3A не подходит — коннектор поддерживает только access/secret key), бакет `weather-raw` (то же имя, что у MinIO-бакета в `docker-compose.yml`, чтобы не менять object-key конвенцию), k8s Secret в namespace `dm-pipeline`.

Postgres-таблицы `weather_actual`/`weather_forecast` удалены из `backend/infra/postgres/init.sql` — Postgres остаётся задеплоенным (chart `backend/deploy/helm/postgres/`), но пустым, зарезервирован под будущие данные `front_api`.

### Сквозная проверка S3-прямого пути (08.07.2026, задеплоено и прогнано на кластере)

Задеплоено: `terraform apply` (боевой бакет `weather-raw` + сервис-аккаунт + k8s Secret `weather-raw-s3` в `dm-pipeline`), wipe+reinstall `postgres`-чарта (пустая схема), пересборка/пуш `dm-pipeline-image`/`dm-trigger-image` (`docker buildx ... --push` + `helm upgrade`), ручное создание топика `weather.forecast.raw.created` на брокере (не auto-create).

В процессе поймано и исправлено (уже в финальном коде, не в этом абзаце как история):
- `dag_run_id`/`event_id` — изначально в `dm_trigger` суффикс `-{business_date}` дописывался прямо к `event_id`, а `event_id` попадает в ClickHouse `event_id UUID` колонку → `UUID string too large`. Исправлено: `event_id` остаётся настоящим UUID из манифеста, уникальность per-date живёт только в `dag_run_id` (`airflow_client.py`); имя result-файла джобы взято из `dag_run.run_id` (гарантированно уникален), а не из `event_id`/`trace_id` (оба общие на несколько дат одного манифеста).
- `event_created_at` — `Spark`'ов `to_timestamp(lit, "yyyy-MM-dd'T'HH:mm:ssXXX")` молча возвращал `NULL` на ISO8601 с дробными секундами (`...346619Z`), что упало на `NOT NULL` колонке в ClickHouse. Исправлено: парсинг через `datetime.fromisoformat` в Python до передачи в Spark, а не через фиксированный формат внутри Spark SQL.
- Топик `weather.forecast.raw.created` создать напрямую из пода `kafka` не получилось (`Timed out waiting to send the call` — тот же класс hairpin/CNI-проблемы с self-referencing запросами внутри самого kafka-пода, что уже фиксировался раньше в этом проекте); создан успешно с первой попытки из пода `dm-trigger`.

Прогнано и подтверждено на кластере (станция `wmo_index=20674`, дата `1960-01-01`):
- actual: raw JSON в S3 (`actual/date=1960-01-01.json`) → `weather.actual.raw.created` → `dm_trigger` триггерит DAG → Spark читает `s3a://weather-raw/...` напрямую → `dm_fct_daily_weather_current` заполнилась корректными значениями (temperature -31.9/-27.5, temp_min -35.1/-29, temp_max -25.9/-24.6 для двух станций);
- forecast: raw JSON (`forecast/date=1960-01-01.json`, намеренно другие значения) → `weather.forecast.raw.created` → `dm_fct_daily_forecast_current` заполнилась, `dm_fct_forecast_error_current` посчиталась корректно: `temperature_error=1.9`, `temp_min_error=2.1`, `temp_max_error=1.9`, `precipitation_mm_error=0.5` (знаковая, `forecast-actual`), `actual_trace_id`/`forecast_trace_id` указывают на исходные события;
- идемпотентность: повторная публикация того же forecast-манифеста (новый `event_id`, тот же `business_date`) не задублировала ни `dm_fct_daily_forecast`, ни `dm_fct_forecast_error` (оба остались на 1 строке);
- путь ошибки: манифест с несуществующим S3-объектом (`actual/date=1999-09-09.json`) — DAG падает предсказуемо (Spark кидает `FileNotFoundException` на `s3a://`-чтении), `on_failure_callback` публикует `weather.pipeline.failed{stage: dm, reason: dag_task_failed}` с правильным `trace_id` — поведение то же самое (явный `pipeline.failed`, не тихий no-op), что и до перехода на S3.

Нод-пул кластера расширен до 4vCPU/8GB под эту нагрузку (`terraform/bootstrap/kubernetes-nodegroup.tf`, применено); memory limit `airflow`-чарта поднят 4Gi→5Gi под добавленный S3A-коннектор в classpath Spark-драйвера (`backend/deploy/helm/airflow/values.yaml`) — на прогонах выше проблем с памятью не было.

**Вывод:** план в целом рабочий и логически связный (событийная цепочка с S3 как единственным промежуточным хранилищем и Kafka как шиной). Разрыв — всё, что после `weather.dm.ready`: `analytics_api` целиком не реализован.

### Батчинг dm_pipeline: один DAG-ран на манифест, не на день (09.07.2026)

`dm_trigger` изначально фанаутил один манифест (`object_keys` на несколько дат) в N отдельных Airflow DAG-ранов — по одному на дату, каждый свой `spark-submit`/JVM. На широких диапазонах (месяцы) это порождало десятки-сотни DAG-ранов на один пользовательский запрос и упиралось в память Airflow-пода (несколько одновременных JVM в одном контейнере уже роняли под OOM — см. инцидент с runaway-тестом на годы вперёд и последующее урезание `AIRFLOW__CORE__PARALLELISM`/`MAX_ACTIVE_TASKS_PER_DAG` до 3).

Исправлено: `dm_trigger` теперь триггерит **один** DAG-ран на манифест, передавая весь `date_from`/`date_to` через `dag_run.conf` вместо одной `business_date`. Spark-джоба (`s3_to_clickhouse.py`) сама детерминированно строит список S3-ключей на каждый день диапазона (`{prefix}/date=<day>.json`, где `prefix` зависит от `dataset_type`) и читает их одним `spark.read.json([...])` — Spark нативно принимает список путей. RAW/ODS/DM пишутся построчно как и раньше (идемпотентность на уровне `ReplacingMergeTree` не завязана на "один файл = одна джоба", схему ClickHouse трогать не пришлось), пересчёт `dm_fct_forecast_error` использует `.between(date_from, date_to)` вместо равенства одной дате. `weather.dm.ready` соответственно несёт `date_from`/`date_to` вместо `observation_date` — одно событие означает "весь диапазон трейса обработан".

Побочный эффект: чинит скрытый баг преждевременного `ready` в `analytics_api` (`dm_events_handler.py`, `_on_trace_resolved`) — раньше `pending_trace_ids` резолвился по **первому** пришедшему `weather.dm.ready` с этим `trace_id`, а таких событий было по одному на день; запрос на 31 день теоретически мог получить `ready` уже после 1 обработанного дня из 27 недостающих. Теперь на trace_id приходит ровно одно `weather.dm.ready`, покрывающее весь диапазон — правок в `analytics_api` для этого не потребовалось.

После батчинга `AIRFLOW__CORE__PARALLELISM`/`MAX_ACTIVE_TASKS_PER_DAG`/`MAX_ACTIVE_RUNS_PER_DAG` подняты обратно `3` → `8` — один пользовательский запрос теперь порождает максимум 2 DAG-рана (actual+forecast) независимо от ширины диапазона дат, риск повторного OOM от объёма данных на JVM не растёт (месяц дневных файлов — по-прежнему сотни строк, не big data), растёт только количество *одновременных разных* запросов.

## Принятые решения

1. **Клиент ↔ analytics_api: поллинг, не held-open HTTP.** `analytics_api` на cache-miss сразу отвечает `202 Accepted {request_id, poll_url}` и не блокирует поток/соединение на всю глубину пайплайна. Прогресс отслеживается через таблицу `request_status` (PostgreSQL или отдельная схема в `analytics_api`), ключ — `trace_id`; каждый Kafka-consumer в `analytics_api` (`weather.dm.ready`, `weather.pipeline.failed`) только обновляет строку по `trace_id`, GET `/requests/{id}` её читает. WebSocket/SSE как более отзывчивая альтернатива поллингу — не в скоупе сейчас, можно добавить позже без смены модели данных.
2. **Триггер Airflow — отдельный сервис `dm_trigger`.** Consumer `weather.actual.raw.created`/`weather.forecast.raw.created`, единственная обязанность — вызвать Airflow REST API `POST /dags/{dag_id}/dagRuns` с `conf` (включая `dataset_type`/`bucket`/`date_from`/`date_to` — один DAG-ран на манифест, не на дату) и обработать ответ (retry / `weather.pipeline.failed` при неуспехе). Не часть `analytics_api` — чтобы Airflow-специфичный код (auth, retry-политика конкретно под Airflow API) не тёк в бизнес-сервисы.
3. **Spark делает трансформацию; SQL-файлы `infra/clickhouse/pipeline/*.sql` — эталон/acceptance-спецификация, не исполняемый пайплайн.** PySpark job (запускается `BashOperator`/`spark-submit` из Airflow DAG) сам читает S3, трансформирует RAW→ODS→DM и пишет в ClickHouse. `01_raw_load.sql`…`03_dm_fct_daily_weather.sql` остаются как документированная спецификация того, что каждый слой обязан содержать (по ним можно писать data-quality тесты/сверку результата Spark-джобы), но в проде их текст напрямую не гоняется.
4. **Единый контракт ошибки `weather.pipeline.failed`.** Публикуется любым шагом на любой сбой: `{event_id, trace_id, event_type: "weather.pipeline.failed", stage: fetch|dm_trigger|dm, source_name, reason, details, schema_version, created_at}`. В частности, `historical_fetcher` должен публиковать его вместо тихого `ack.acknowledge()` в случае `s3Keys.isEmpty()` (`EventProcessor.java:147`) — «нет данных за период» это тоже терминальный исход для `analytics_api`, а не просто лог. `analytics_api` консьюмит этот topic наравне с `weather.dm.ready` и переводит `request_status` в `FAILED` с `stage`/`reason` от источника. Таймаут на стороне `analytics_api` (на случай, если событие само потеряется) — отдельная защита, не исключает основной канал через событие.
5. **Прогнозная ветка переиспользует существующий DAG/топики-паттерн, без дублирования инфраструктуры.** `dataset_type` (`"actual"`|`"forecast"`) — дискриминатор, но теперь определяется тем, из какого топика пришёл манифест (`weather.actual.raw.created` vs `weather.forecast.raw.created`), а не отдельным полем события. `dm_trigger` пробрасывает его в `dag_run.conf`, DAG передаёт Spark-джобе через `--dataset-type`, джоба по нему выбирает целевые ClickHouse-таблицы (`*_weather`/`*_forecast`). Один DAG, один Airflow-эндпоинт — вместо параллельной инфраструктуры под прогнозы. Ошибка прогноза в `dm_fct_forecast_error` считается и знаково (`forecast - actual`, показывает смещение), и абсолютно (`|forecast - actual|`, для агрегатной точности вроде MAE) — по каждой метрике (`temperature`, `temp_min`, `temp_max`, `precipitation_mm`); пересчитывается после каждой DM-записи (в любой из двух веток) через `inner join` `dm_fct_daily_weather`×`dm_fct_daily_forecast` по `(wmo_index, day)` — если второй стороны ещё нет, join пуст и ничего не пишется, витрина дозаполнится независимо от порядка прихода actual/forecast.
6. **Postgres убран из пути погодных данных; Spark читает S3 напрямую; `etl_service` удалён.** Раньше: `historical_fetcher` → S3 → `etl_service` (upsert в Postgres `weather_actual`) → `weather.clean.created` → `dm_trigger` → DAG → Spark (JDBC-чтение Postgres) → ClickHouse. Решено убрать промежуточный Postgres-слой целиком: `dm_trigger` подписан напрямую на манифест-топики (`weather.actual.raw.created`/`weather.forecast.raw.created`), Spark читает сырой JSON прямо из S3 (`s3a://`, Hadoop S3A-коннектор, `hadoop-aws`+`aws-java-sdk-bundle` в classpath). Причины: (a) убирает лишний хоп и сервис, который только копировал данные из одного хранилища в другое без добавления бизнес-логики; (b) Postgres остаётся живым, но теперь зарезервирован под будущие пользовательские данные `front_api`, а не под погодные факты. Боевой S3-бакет — managed Yandex Object Storage (не MinIO-в-кластере): консистентно с тем, что Postgres тоже managed (`terraform/stage-1/postgresql.tf`), и не грузит небольшой k8s-кластер ещё одним stateful workload'ом. Таблицы `weather_actual`/`weather_forecast` удалены из `infra/postgres/init.sql`.

## Что нужно завести дополнительно (относительно текущего кода)

Сделано (08.07.2026, задеплоено на k8s namespace `dm-pipeline`):
- ~~Новый topic `weather.dm.ready` + `weather.pipeline.failed`~~ — в `contracts/topics.json` и `contracts/events/`.
- ~~Новый микросервис `dm_trigger`~~ — `backend/microservices/dm_trigger/`, теперь consumer `weather.actual.raw.created`+`weather.forecast.raw.created` напрямую.
- ~~Airflow + Spark~~ — `backend/microservices/dm_pipeline/` (lean: `airflow standalone`, LocalExecutor, PySpark `local[2]` в том же поде), Helm-чарты в `backend/deploy/helm/{kafka,postgres,clickhouse,airflow,dm-trigger}`.
- ~~PySpark job~~ — `spark_jobs/s3_to_clickhouse.py`, читает S3 напрямую, реальная ClickHouse-схема `infra/clickhouse/schema.sql`.
- ~~Прогнозная ветка (`dataset_type`-ветвление в `dm_trigger`/DAG/Spark, таблицы `raw_forecast_events`/`ods_daily_forecast`/`dm_fct_daily_forecast`, витрина ошибки `dm_fct_forecast_error`)~~ — `backend/infra/clickhouse/schema.sql`; новый контракт `weather.forecast.raw.created` в `contracts/`.
- ~~Убрать Postgres из пути погодных данных~~ — `etl_service` удалён, `weather_actual`/`weather_forecast` убраны из `infra/postgres/init.sql`, Spark читает S3 напрямую.
- ~~Боевой S3~~ — `yandex-cloud-sample/terraform/stage-1/object_storage.tf` (managed Yandex Object Storage, бакет `weather-raw`).

Ещё не сделано:
- Реализация `analytics_api` целиком: HTTP-роуты (`POST /weather`, `GET /requests/{id}`), таблица/хранилище `request_status`, kafka-продюсер (`weather.need_info`) и consumer (`weather.dm.ready` + `weather.pipeline.failed`), ClickHouse-клиент.
- Правка `historical_fetcher`: публиковать `weather.pipeline.failed` вместо молчаливого `ack.acknowledge()` при `s3Keys.isEmpty()`.
- Деплой существующих микросервисов (`historical_fetcher`, будущий `analytics_api`) на тот же k8s-кластер — сейчас они есть только в локальном `docker-compose`/отдельно, `dm-pipeline`-namespace их не содержит.
- `.sourcecraft/ci.yaml` для `se26` — сейчас всё собрано/задеплоено вручную (`docker build/push` + `helm upgrade --install`, `terraform apply` для облачной инфры).
