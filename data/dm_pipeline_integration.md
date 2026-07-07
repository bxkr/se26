# Как подключиться к dm_trigger/Airflow/Spark/ClickHouse

Что построено в этом раунде и как остальным сервисам (`etl_service`, будущий `analytics_api`) этим воспользоваться. Общая схема и дизайн-решения — `data/pipeline_flow.md`, здесь — конкретика для интеграции.

## Что уже работает

Задеплоено на k8s-кластере (namespace `dm-pipeline`), задача **etl_service публикует `weather.clean.created`** — и дальше всё происходит само:

```
weather.clean.created (Kafka) → dm_trigger → Airflow DAG dm_pipeline → PySpark → ClickHouse → weather.dm.ready (Kafka)
```

Сквозная цепочка (Kafka → dm_trigger → Airflow → Spark → ClickHouse → Kafka) проверена вручную и работает, включая идемпотентность повторных прогонов и путь ошибки.

## 1. Что должен сделать `etl_service`

После успешной записи в `weather_actual` (в `writer.py`, после `writer.write(...)`) нужно опубликовать событие в топик **`weather.clean.created`** (уже существует в `contracts/topics.json`, партиций хватает). Пока этого нет — цепочка эмулируется вручную для тестов.

**Важно: одно событие на одну `observation_date`.** Если в одном `weather.actual.raw.created` пришло несколько дат (несколько файлов в `object_keys`), нужно опубликовать по одному `weather.clean.created` на каждую дату — `dm_trigger` триггерит один DAG run на одно событие, а Spark-джоба обрабатывает ровно один `business_date` за прогон.

Контракт (`contracts/events/weather.clean.created.example.json`):

```json
{
  "event_id": "b1f588fc-3272-4fcb-a813-cc78085b5f84",
  "trace_id": "1c0aa3e8-2aa8-4d0b-8c7e-a37d7fa4fb4e",
  "event_type": "weather.clean.created",
  "dataset_type": "actual",
  "source_event_id": "8f60b5dc-99f9-4dc0-a7c1-04b4be1635ec",
  "observation_date": "1960-01-01",
  "record_count": 2,
  "schema_version": 1,
  "created_at": "2026-07-06T12:15:00Z"
}
```

Обязательные поля, которые реально использует `dm_trigger`: **`trace_id`** (пробрасывается без изменений через всю цепочку до `weather.dm.ready`/`weather.pipeline.failed` — по нему `analytics_api` будет сопоставлять ответ с исходным запросом клиента) и **`observation_date`** (= `business_date` для Airflow DAG и Spark-джобы). Без них `dm_trigger` не триггерит DAG, а публикует `weather.pipeline.failed{stage: dm_trigger, reason: dm_trigger_failed}`.

Источник данных для Spark-джобы — сама таблица `weather_actual` (та, что уже пишет `etl_service`), в неё ничего добавлять не нужно.

### Что должен сделать будущий `predict_fetcher`

Симметрично `etl_service`, но для прогнозов: писать строки в **`weather_forecast`** (Postgres, та же схема, что у `weather_actual` — см. `backend/infra/postgres/init.sql`; сейчас это временный ручной stand-in, т.к. `predict_fetcher` ещё не создан) и публиковать `weather.clean.created` с **`dataset_type: "forecast"`** и `observation_date` = дата, на которую сделан прогноз. Один ивент на дату, как и у actual. Остальное (dm_trigger → DAG → Spark → `dm_fct_daily_forecast` → `weather.dm.ready`) уже готово это принять — ничего сверх этого от `predict_fetcher` не требуется.

## 2. Что нужно сделать в `analytics_api`

Consume два топика:

- **`weather.dm.ready`** — данные посчитаны и лежат в ClickHouse. Пример:
  ```json
  {
    "event_id": "3a2f7d5e-...",
    "trace_id": "1c0aa3e8-...",
    "event_type": "weather.dm.ready",
    "dataset_type": "actual",
    "observation_date": "1960-01-01",
    "record_count": 2,
    "schema_version": 1,
    "created_at": "2026-07-06T12:20:00Z"
  }
  ```
- **`weather.pipeline.failed`** — сбой на любом шаге (fetch/etl/dm_trigger/dm). Пример:
  ```json
  {
    "event_id": "9d1b2c3a-...",
    "trace_id": "1c0aa3e8-...",
    "event_type": "weather.pipeline.failed",
    "stage": "dm",
    "source_name": "dm_pipeline",
    "reason": "dag_task_failed",
    "details": "человекочитаемое описание ошибки",
    "schema_version": 1,
    "created_at": "2026-07-06T12:20:00Z"
  }
  ```

По `trace_id` из любого из двух событий — обновить `request_status` (см. `pipeline_flow.md`, «Принятые решения» п.1): `READY` + прочитать данные из ClickHouse, либо `FAILED` + `stage`/`reason`/`details`.

### Чтение данных из ClickHouse

Витрина — `weather.dm_fct_daily_weather` (`ReplacingMergeTree`, дедуп через `FINAL`; либо готовая вьюха `weather.dm_fct_daily_weather_current`, уже с `FINAL` внутри):

```sql
SELECT wmo_index, day, temperature, temp_min, temp_max, precipitation_mm
FROM weather.dm_fct_daily_weather_current
WHERE day = '1960-01-01';
```

Промежуточные слои (для отладки, не для чтения `analytics_api`): `weather.raw_weather_events` (аудит-зеркало `weather_actual`), `weather.ods_daily_weather` / `weather.ods_daily_weather_current`.

Прогнозы — зеркальные таблицы/вьюхи: `weather.dm_fct_daily_forecast_current` (та же форма, что у actual-витрины):

```sql
SELECT wmo_index, day, temperature, temp_min, temp_max, precipitation_mm
FROM weather.dm_fct_daily_forecast_current
WHERE day = '1960-01-01';
```

Ошибка прогноза (знаковая `forecast-actual` + абсолютная, на каждую метрику) — `weather.dm_fct_forecast_error_current`, заполняется автоматически, когда за одну и ту же `(wmo_index, day)` есть и actual, и forecast:

```sql
SELECT wmo_index, day,
       temperature_error, temperature_abs_error,
       temp_min_error, temp_min_abs_error,
       temp_max_error, temp_max_abs_error,
       precipitation_mm_error, precipitation_mm_abs_error
FROM weather.dm_fct_forecast_error_current
WHERE day = '1960-01-01';
```

Полная схема — `backend/infra/clickhouse/schema.sql`.

## 3. Как подключиться к сервисам (реквизиты)

Всё поднято в namespace **`dm-pipeline`** на том же k8s-кластере, что и `historical-data` (другой репозиторий). Адреса ниже — **внутрикластерные** DNS-имена (`<service>.dm-pipeline.svc.cluster.local`, короткая форма `<service>` работает из подов в том же namespace). Снаружи кластера напрямую не достучаться — см. раздел 4 про port-forward для локальной разработки.

| Сервис | Адрес изнутри кластера | Креды |
|---|---|---|
| Kafka | `kafka:9092` | без auth |
| ClickHouse (HTTP) | `clickhouse:8123` | user `default`, password `weather`, db `weather` |
| ClickHouse (native) | `clickhouse:9000` | то же |
| Airflow REST API | `http://airflow:8080/api/v1/...` | Basic Auth `admin:admin` |
| Postgres (operational, стенд) | `postgres:5432` | db `weather`, user `weather`, password `weather` |

**Важно:** `postgres:5432` — это **временный стенд** со схемами `weather_actual` и `weather_forecast` (та же DDL, что в `infra/postgres/init.sql`), поднятый только для тестирования этого среза пайплайна, а не боевая БД `etl_service`/`predict_fetcher` (те пока живут в локальном `docker-compose` либо не созданы, на кластере не задеплоены). Когда `etl_service`/`predict_fetcher` тоже будут задеплоены в `dm-pipeline` (или другой namespace на этом кластере) — Spark-джобу нужно перенаправить на их Postgres через `helm upgrade airflow --set weatherPostgres.host=<новый-host>` (см. `backend/deploy/helm/airflow/values.yaml`, секция `weatherPostgres`).

**Креды везде dev-grade** (`admin/admin`, `weather/weather`) — это осознанный выбор для лабораторного/учебного стенда, не для чего-то с реальными данными.

## 4. Как проверить/поработать с этим локально

Прямого доступа снаружи кластера нет (ClusterIP-сервисы, без Ingress). Для локальной разработки — `kubectl port-forward`:

```bash
kubectl port-forward -n dm-pipeline svc/kafka 9092:9092
kubectl port-forward -n dm-pipeline svc/clickhouse 8123:8123
kubectl port-forward -n dm-pipeline svc/airflow 8080:8080
kubectl port-forward -n dm-pipeline svc/postgres 5432:5432
```

После этого локально работают `localhost:9092` (Kafka), `http://localhost:8123` (ClickHouse HTTP), `http://localhost:8080` (Airflow UI/REST, `admin`/`admin`), `localhost:5432` (Postgres).

Быстрая ручная проверка сквозного пути (без реального `etl_service`) — вставить строку в `weather_actual` и опубликовать `weather.clean.created` вручную:

```bash
# 1. тестовая строка (через локальный psql после port-forward, либо kubectl exec)
psql "postgresql://weather:weather@localhost:5432/weather" -c "
INSERT INTO weather_actual (
  source_name, observation_date, wmo_index, station_name, country,
  min_temp, avg_temp, max_temp, precipitation,
  raw_bucket, raw_object_key, event_id, trace_id, event_created_at
) VALUES (
  'historical_fetcher', '1960-01-01', '20674', 'Диксон', 'Россия',
  -35.1, -31.9, -25.9, 0,
  'weather-raw', 'actual/date=1960-01-01.json', gen_random_uuid(), gen_random_uuid(), now()
) ON CONFLICT (source_name, observation_date, wmo_index) DO UPDATE SET event_id = EXCLUDED.event_id;
"

# 2. weather.clean.created (Python, kafka-python; trace_id должен совпадать с той строкой)
python3 -c "
import json, uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=lambda v: json.dumps(v).encode())
producer.send('weather.clean.created', {
    'event_id': str(uuid.uuid4()), 'trace_id': str(uuid.uuid4()),
    'event_type': 'weather.clean.created', 'dataset_type': 'actual',
    'source_event_id': str(uuid.uuid4()), 'observation_date': '1960-01-01',
    'record_count': 1, 'schema_version': 1,
    'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
})
producer.flush()
"

# 3. проверить результат (через ~10-20с)
curl -s -u admin:admin http://localhost:8080/api/v1/dags/dm_pipeline/dagRuns | python3 -m json.tool
```

Через несколько секунд после `success` — строка появится в `weather.dm_fct_daily_weather_current` (ClickHouse), а в топике `weather.dm.ready` — событие с тем же `trace_id`.

### Проверка прогнозной ветки + витрины ошибки

Дополнительно к шагам выше — вставить прогнозную строку для **той же** `(wmo_index, observation_date)`, что уже есть в `weather_actual`, с намеренно другими значениями метрик, и опубликовать `weather.clean.created{dataset_type: "forecast"}`:

```bash
# 1. тестовая строка прогноза (та же дата/станция, что и в weather_actual выше)
psql "postgresql://weather:weather@localhost:5432/weather" -c "
INSERT INTO weather_forecast (
  source_name, observation_date, wmo_index, station_name, country,
  min_temp, avg_temp, max_temp, precipitation,
  raw_bucket, raw_object_key, event_id, trace_id, event_created_at
) VALUES (
  'predict_fetcher', '1960-01-01', '20674', 'Диксон', 'Россия',
  -33.0, -30.0, -24.0, 0.5,
  'weather-raw', 'forecast/date=1960-01-01.json', gen_random_uuid(), gen_random_uuid(), now()
) ON CONFLICT (source_name, observation_date, wmo_index) DO UPDATE SET event_id = EXCLUDED.event_id;
"

# 2. weather.clean.created с dataset_type=forecast
python3 -c "
import json, uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=lambda v: json.dumps(v).encode())
producer.send('weather.clean.created', {
    'event_id': str(uuid.uuid4()), 'trace_id': str(uuid.uuid4()),
    'event_type': 'weather.clean.created', 'dataset_type': 'forecast',
    'source_event_id': str(uuid.uuid4()), 'observation_date': '1960-01-01',
    'record_count': 1, 'schema_version': 1,
    'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
})
producer.flush()
"

# 3. через ~10-20с проверить dm_fct_forecast_error (актуальный этот раз должен уже быть в ClickHouse из шага выше)
curl -s -u admin:admin http://localhost:8080/api/v1/dags/dm_pipeline/dagRuns | python3 -m json.tool
```

После `success` — `weather.dm_fct_daily_forecast_current` заполнится прогнозной строкой, а `weather.dm_fct_forecast_error_current` — строкой с разницей между actual и forecast по всем 4 метрикам за `1960-01-01`. Порядок публикации (actual/forecast) не важен — витрина ошибки досчитывается тем прогоном, который приходит вторым.

## 5. Где что лежит в репозитории

| Что | Путь |
|---|---|
| `dm_trigger` (код) | `backend/microservices/dm_trigger/` |
| Airflow DAG + PySpark job | `backend/microservices/dm_pipeline/` |
| Реальная ClickHouse-схема | `backend/infra/clickhouse/schema.sql` |
| Контракты событий | `backend/contracts/` (`topics.json`, `events/*.example.json`) |
| Helm-чарты для деплоя | `backend/deploy/helm/{kafka,postgres,clickhouse,airflow,dm-trigger}` |
| Дизайн-документ / статус реализации | `data/pipeline_flow.md` |

## 6. Известные ограничения (осознанно, не баги)

- Нет `.sourcecraft/ci.yaml` для `se26` — всё собрано и задеплоено вручную (`docker buildx build --platform linux/amd64 ... --push` + `helm upgrade --install`). Если нужно пересобрать после правок в `dm_trigger`/`dm_pipeline` — тот же ручной процесс, пока CI не заведён.
- `postgres`-чарт — временный стенд, не боевая БД `etl_service` (см. п.3).
- Airflow — `standalone` (webserver+scheduler+triggerer в одном поде, `LocalExecutor`), не рассчитан на серьёзную нагрузку — это осознанный lean-выбор под объём данных этого проекта, не production-паттерн.
- DAG `dm_pipeline` без расписания — только внешний триггер через `dm_trigger`.
