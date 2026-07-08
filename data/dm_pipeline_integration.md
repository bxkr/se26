# Как подключиться к dm_trigger/Airflow/Spark/ClickHouse

Что построено в этом раунде и как остальным сервисам (`historical_fetcher`, будущие `predict_fetcher`/`analytics_api`) этим воспользоваться. Общая схема и дизайн-решения — `data/pipeline_flow.md`, здесь — конкретика для интеграции.

## Что уже работает

Задеплоено на k8s-кластере (namespace `dm-pipeline`). `etl_service` больше не существует — `dm_trigger` подписан напрямую на манифест-топики:

```
weather.actual.raw.created | weather.forecast.raw.created (Kafka)
  → dm_trigger → Airflow DAG dm_pipeline → PySpark (читает S3 напрямую) → ClickHouse → weather.dm.ready (Kafka)
```

Сквозная цепочка (Kafka → dm_trigger → Airflow → Spark → ClickHouse → Kafka) проверяется вручную — см. раздел 4.

## 1. Что должен делать `historical_fetcher` (уже делает, без изменений)

Кладёт сырой daily JSON в S3 (бакет `weather-raw`, ключ `actual/date=YYYY-MM-DD.json`) и публикует манифест в топик **`weather.actual.raw.created`** (уже существует в `contracts/topics.json`). Ничего в этой части менять не нужно — `dm_trigger` теперь читает этот топик напрямую вместо `etl_service`.

Контракт (`contracts/events/weather.actual.raw.created.example.json`):

```json
{
  "event_id": "8f60b5dc-99f9-4dc0-a7c1-04b4be1635ec",
  "trace_id": "1c0aa3e8-2aa8-4d0b-8c7e-a37d7fa4fb4e",
  "event_type": "weather.actual.raw.created",
  "source_name": "historical_fetcher",
  "bucket": "weather-raw",
  "object_keys": ["actual/date=1960-01-01.json", "actual/date=1960-01-02.json"],
  "date_from": "1960-01-01",
  "date_to": "1960-01-02",
  "schema_version": 1,
  "created_at": "2026-07-06T12:10:00Z"
}
```

`dm_trigger` фанаутит по `object_keys` — один Airflow `DagRun` на каждую дату. Обязательные поля: **`trace_id`**, **`bucket`**, **`object_keys`** (непустой список, каждый ключ должен матчить `date=YYYY-MM-DD.json`). Без них `dm_trigger` не триггерит DAG, а публикует `weather.pipeline.failed{stage: dm_trigger, reason: dm_trigger_invalid_event}`.

Формат самого raw JSON-файла в S3 (то, что читает Spark) — без изменений:

```json
{
  "date": "1960-01-01",
  "stations": [
    {"wmo_index": 20674, "name": "Диксон", "country": "Россия", "min_temp": -35.1, "avg_temp": -31.9, "max_temp": -25.9, "precipitation": 0}
  ]
}
```

### Что должен сделать будущий `predict_fetcher`

Симметрично `historical_fetcher`, но для прогнозов: писать raw JSON (та же структура `{date, stations:[...]}`) в S3 по ключу **`forecast/date=YYYY-MM-DD.json`** и публиковать манифест в новый топик **`weather.forecast.raw.created`** (тот же формат, что `weather.actual.raw.created`, `source_name: "predict_fetcher"`, см. `contracts/events/weather.forecast.raw.created.example.json`). Остальное (`dm_trigger` → DAG → Spark → `dm_fct_daily_forecast`/`dm_fct_forecast_error` → `weather.dm.ready`) уже готово это принять — ничего сверх этого от `predict_fetcher` не требуется. Раньше это была временная Postgres-таблица `weather_forecast` — она удалена вместе с переходом на S3-прямой источник (см. `pipeline_flow.md`, «Принятые решения», п.6).

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
- **`weather.pipeline.failed`** — сбой на любом шаге (fetch/dm_trigger/dm). Пример:
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

Промежуточные слои (для отладки, не для чтения `analytics_api`): `weather.raw_weather_events` (аудит-зеркало исходного S3-файла), `weather.ods_daily_weather` / `weather.ods_daily_weather_current`.

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
| S3 (Object Storage) | `https://storage.yandexcloud.net`, bucket `weather-raw` | статический ключ, см. Secret `weather-raw-s3` в namespace `dm-pipeline` (создан Terraform'ом, `yandex-cloud-sample/terraform/stage-1/object_storage.tf`) |
| Postgres (operational) | `postgres:5432` | db `weather`, user `weather`, password `weather` |

**Важно:** `postgres:5432` больше **не в пути погодных данных** — таблицы `weather_actual`/`weather_forecast` удалены (см. `pipeline_flow.md`, «Принятые решения», п.6). Chart остаётся задеплоенным, пустая база зарезервирована под будущие данные `front_api`. Весь путь погодных данных теперь идёт через S3 (`weather-raw`) — Spark читает raw JSON оттуда напрямую.

**Креды везде dev-grade** (`admin/admin`, `weather/weather`) — это осознанный выбор для лабораторного/учебного стенда, не для чего-то с реальными данными. S3-ключи — не dev-grade (реальные Yandex Cloud static keys); они никогда не проходят через `values.yaml`/`helm --set` — Terraform создаёт k8s Secret `weather-raw-s3` напрямую в кластере, `airflow`-чарт лишь ссылается на него по имени (`envFrom.secretRef`, см. `deploy/helm/airflow/values.yaml` → `s3.secretName`).

## 4. Как проверить/поработать с этим локально

Прямого доступа снаружи кластера нет (ClusterIP-сервисы, без Ingress). Для локальной разработки — `kubectl port-forward`:

```bash
kubectl port-forward -n dm-pipeline svc/kafka 9092:9092
kubectl port-forward -n dm-pipeline svc/clickhouse 8123:8123
kubectl port-forward -n dm-pipeline svc/airflow 8080:8080
```

После этого локально работают `localhost:9092` (Kafka), `http://localhost:8123` (ClickHouse HTTP), `http://localhost:8080` (Airflow UI/REST, `admin`/`admin`).

### Проверка сквозного потока

Без реального `historical_fetcher`/`predict_fetcher` — положить тестовый raw JSON в S3 (боевой бакет `weather-raw`, через `aws s3 cp`/boto3 с ключами из Terraform output или Secret `weather-raw-s3`) и опубликовать манифест вручную:

```bash
# 1. тестовый raw JSON в S3 (endpoint/ключи — см. раздел 3)
python3 -c "
import boto3, json
s3 = boto3.client('s3', endpoint_url='https://storage.yandexcloud.net',
                   aws_access_key_id='<ACCESS_KEY>', aws_secret_access_key='<SECRET_KEY>')
payload = {
    'date': '1960-01-01',
    'stations': [{'wmo_index': 20674, 'name': 'Диксон', 'country': 'Россия',
                  'min_temp': -35.1, 'avg_temp': -31.9, 'max_temp': -25.9, 'precipitation': 0}],
}
s3.put_object(Bucket='weather-raw', Key='actual/date=1960-01-01.json',
              Body=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
              ContentType='application/json; charset=utf-8')
"

# 2. манифест weather.actual.raw.created (Python, kafka-python, через port-forward на localhost:9092)
python3 -c "
import json, uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=lambda v: json.dumps(v).encode())
producer.send('weather.actual.raw.created', {
    'event_id': str(uuid.uuid4()), 'trace_id': str(uuid.uuid4()),
    'event_type': 'weather.actual.raw.created', 'source_name': 'historical_fetcher',
    'bucket': 'weather-raw', 'object_keys': ['actual/date=1960-01-01.json'],
    'date_from': '1960-01-01', 'date_to': '1960-01-01', 'schema_version': 1,
    'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
})
producer.flush()
"

# 3. проверить результат (через ~10-20с)
curl -s -u admin:admin http://localhost:8080/api/v1/dags/dm_pipeline/dagRuns | python3 -m json.tool
```

Через несколько секунд после `success` — строка появится в `weather.dm_fct_daily_weather_current` (ClickHouse), а в топике `weather.dm.ready` — событие с тем же `trace_id`.

`tools/test_producer` (локальный docker-compose) может выполнить только шаги 1-2 против **локального** MinIO/Kafka (`docker compose --profile test up test_producer`) — оно проверяет, что S3-загрузка и Kafka-паблиш синтаксически работают, но не может проверить `dm_trigger`/Airflow/Spark/ClickHouse, потому что они существуют только на k8s-кластере, не в `docker-compose.yml`. Полная сквозная проверка — только шаги выше, против кластера.

### Проверка прогнозной ветки + витрины ошибки

Дополнительно к шагам выше — положить прогнозный raw JSON для **той же** `(wmo_index, date)`, что уже проверялась выше, с намеренно другими значениями метрик, ключ `forecast/date=...json`, топик `weather.forecast.raw.created`:

```bash
# 1. тестовый прогнозный raw JSON (та же дата/станция, что и в шаге 1 выше)
python3 -c "
import boto3, json
s3 = boto3.client('s3', endpoint_url='https://storage.yandexcloud.net',
                   aws_access_key_id='<ACCESS_KEY>', aws_secret_access_key='<SECRET_KEY>')
payload = {
    'date': '1960-01-01',
    'stations': [{'wmo_index': 20674, 'name': 'Диксон', 'country': 'Россия',
                  'min_temp': -33.0, 'avg_temp': -30.0, 'max_temp': -24.0, 'precipitation': 0.5}],
}
s3.put_object(Bucket='weather-raw', Key='forecast/date=1960-01-01.json',
              Body=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
              ContentType='application/json; charset=utf-8')
"

# 2. манифест weather.forecast.raw.created
python3 -c "
import json, uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=lambda v: json.dumps(v).encode())
producer.send('weather.forecast.raw.created', {
    'event_id': str(uuid.uuid4()), 'trace_id': str(uuid.uuid4()),
    'event_type': 'weather.forecast.raw.created', 'source_name': 'predict_fetcher',
    'bucket': 'weather-raw', 'object_keys': ['forecast/date=1960-01-01.json'],
    'date_from': '1960-01-01', 'date_to': '1960-01-01', 'schema_version': 1,
    'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
})
producer.flush()
"

# 3. через ~10-20с проверить dm_fct_forecast_error
curl -s -u admin:admin http://localhost:8080/api/v1/dags/dm_pipeline/dagRuns | python3 -m json.tool
```

После `success` — `weather.dm_fct_daily_forecast_current` заполнится прогнозной строкой, а `weather.dm_fct_forecast_error_current` — строкой с разницей между actual и forecast по всем 4 метрикам за `1960-01-01`. Порядок публикации (actual/forecast) не важен — витрина ошибки досчитывается тем прогоном, который приходит вторым.

## 5. Где что лежит в репозитории

| Что | Путь |
|---|---|
| `dm_trigger` (код) | `backend/microservices/dm_trigger/` |
| Airflow DAG + PySpark job | `backend/microservices/dm_pipeline/` (`spark_jobs/s3_to_clickhouse.py`) |
| Реальная ClickHouse-схема | `backend/infra/clickhouse/schema.sql` |
| Контракты событий | `backend/contracts/` (`topics.json`, `events/*.example.json`) |
| Helm-чарты для деплоя | `backend/deploy/helm/{kafka,postgres,clickhouse,airflow,dm-trigger}` |
| Terraform для боевого S3 | `yandex-cloud-sample/terraform/stage-1/object_storage.tf` |
| Дизайн-документ / статус реализации | `data/pipeline_flow.md` |

## 6. Известные ограничения (осознанно, не баги)

- Нет `.sourcecraft/ci.yaml` для `se26` — всё собрано и задеплоено вручную (`docker buildx build --platform linux/amd64 ... --push` + `helm upgrade --install`, плюс `terraform apply` для облачной S3-инфры). Если нужно пересобрать после правок в `dm_trigger`/`dm_pipeline` — тот же ручной процесс, пока CI не заведён.
- `postgres`-чарт — больше не в пути погодных данных, пустая база зарезервирована под `front_api` (см. п.3).
- Airflow — `standalone` (webserver+scheduler+triggerer в одном поде, `LocalExecutor`), не рассчитан на серьёзную нагрузку — это осознанный lean-выбор под объём данных этого проекта, не production-паттерн.
- DAG `dm_pipeline` без расписания — только внешний триггер через `dm_trigger`.
- `tools/test_producer` в локальном `docker-compose` может проверить только загрузку в S3 + паблиш в Kafka — не весь путь (см. раздел 4).
