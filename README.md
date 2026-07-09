<div align=center>
<img height="500" alt="Схема" src="https://github.com/user-attachments/assets/4764a38c-24f5-4577-941e-081930f17232" />
</div>

# se26 — Weather Forecast Accuracy Platform

Событийный (event-driven) сервис, который сравнивает прогнозы погоды с фактическими наблюдениями и показывает,
где и насколько прогноз ошибается. Пайплайн собирает данные из внешних источников, прогоняет их через
Kafka → Airflow/Spark → ClickHouse и отдаёт готовую аналитику через API и веб-интерфейс.

## Что это делает

1. Клиент (веб-интерфейс или API) запрашивает данные за период — по станциям или по регионам.
2. Если данных ещё нет, система асинхронно подтягивает исторические наблюдения и прогнозы за нужный диапазон дат.
3. Данные приземляются в S3 (сырые JSON), затем обрабатываются Spark-джобой в Airflow и попадают в ClickHouse
   слоями RAW → ODS → DM.
4. Для каждой станции и дня считается ошибка прогноза (знаковая и абсолютная) по температуре, мин/макс
   температуре и осадкам.
5. Клиент поллингом получает результат: топ станций/регионов с наибольшей ошибкой прогноза, метрики точности
   модели прогноза, детальный просмотр по станциям.

## Архитектура

Взаимодействие построено на Kafka как шине событий и S3 как промежуточном хранилище сырых данных. Каждый шаг
пайплайна — отдельный микросервис-потребитель одного топика, публикующий результат в следующий.

```
Клиент (frontend)
   │  логин / dashboard / explorer / top-errors / admin
   ▼
front_api  ──────────────────────────────────────────────► Postgres (пользователи), Redis (кэш)
   │  проксирует аналитические запросы
   ▼
analytics_api ── POST /regions|stations/forecast-errors, /errors/top, /metrics/model
   │  кэш-хит? → читает ClickHouse → 200
   │  кэш-мисс → 202 {request_id} + publish weather.need_info, статус в Redis (request_id)
   ▼
historical_fetcher / ForecastFetcher (consume weather.need_info)
   │  тянут данные из внешнего источника → кладут JSON в S3 (bucket weather-raw)
   │  publish weather.actual.raw.created | weather.forecast.raw.created
   ▼
dm_trigger (consume оба топика raw.created)
   │  один манифест = один Airflow DagRun (весь диапазон дат за раз)
   ▼
Airflow DAG dm_pipeline → PySpark job (s3_to_clickhouse.py)
   │  читает JSON прямо из S3 (s3a://) → пишет RAW/ODS/DM слои в ClickHouse
   │  считает витрину dm_fct_forecast_error (join daily_weather × daily_forecast по станции и дню)
   │  publish weather.dm.ready | weather.pipeline.failed (на любой сбой любого шага)
   ▼
analytics_api (consume weather.dm.ready / weather.pipeline.failed)
   │  обновляет статус запроса в Redis по request_id
   ▼
Клиент поллит GET /requests/{request_id} до статуса READY/FAILED
```

`regions_api` — вспомогательный справочный сервис: маппинг метеостанций (`wmo_index`) на регионы РФ,
используется `analytics_api` и `front_api` для группировки по регионам.

## Сервисы

| Сервис | Стек | Роль |
|---|---|---|
| `frontend` | React 19 + TypeScript + Vite + Tailwind, TanStack Query, Visx | Веб-интерфейс: дашборд, поиск по станциям (explorer), топ ошибок, админка |
| `front_api` | Python / FastAPI | Публичный API для фронтенда: аутентификация (JWT), пользователи, проксирование запросов в `analytics_api` |
| `analytics_api` | Python / FastAPI | Основной аналитический API: приём запросов на пересчёт, чтение готовых данных из ClickHouse, оркестрация через Kafka |
| `regions_api` | Python / FastAPI | Справочник метеостанций и регионов |
| `historical_fetcher` | Java / Spring | Получение исторических наблюдений от внешнего источника → S3 |
| `ForecastFetcher` | Java / Spring | Получение прогнозов от внешнего источника → S3 |
| `dm_trigger` | Python | Триггерит Airflow DAG по факту появления новых сырых данных в S3 |
| `dm_pipeline` | Airflow DAG + PySpark | Трансформация RAW → ODS → DM в ClickHouse, расчёт ошибки прогноза |
| `tools/test_producer` | Python | Тестовый продюсер для сквозной проверки пайплайна без ручных запросов |

## Инфраструктура

- **Kafka** — шина событий между сервисами (топики описаны в `backend/contracts/topics.json`, конверт события —
  в `backend/contracts/README.md`).
- **S3 / MinIO** (managed Yandex Object Storage в проде) — хранилище сырых JSON по наблюдениям и прогнозам.
- **ClickHouse** — аналитическое хранилище (RAW/ODS/DM слои + витрина ошибок прогноза).
- **Postgres** — пользователи и служебные данные `front_api`.
- **Redis** — кэш и статусы асинхронных запросов (`request_id → status`).
- **Airflow** — оркестрация ETL-джобы (`dm_pipeline`).
- **Helm-чарты** (`backend/deploy/helm`) — деплой всего стека в Kubernetes.

## Как запустить локально

```bash
cd backend
docker compose up --build
```

Поднимет Postgres, Kafka, MinIO, Redis, ClickHouse и все микросервисы. Порты по умолчанию:

- `front_api` — `localhost:8003`
- `analytics_api` — `localhost:8002`
- `regions_api` — `localhost:8001`
- `historical_fetcher` — `localhost:5050`
- MinIO console — `localhost:9001`, ClickHouse HTTP — `localhost:8123`

Для сквозной проверки пайплайна без ручных запросов:

```bash
docker compose --profile test up test_producer
```

Фронтенд запускается отдельно:

```bash
cd frontend
npm install
npm run dev
```

Чтобы поменять код одного сервиса, правьте его `Dockerfile`/исходники и пересобирайте только этот сервис
(`docker compose up --build <service>`).

## Контракты событий

Формат событий и конвенции описаны в `backend/contracts/README.md`. Каждое событие несёт `event_id`, `trace_id`
(сквозной идентификатор запроса), `event_type`, `schema_version`, `created_at`. Ошибки на любом шаге пайплайна
публикуются единым контрактом `weather.pipeline.failed`, а не проглатываются молча.

Полное описание сквозного потока данных и статус реализации каждого шага — `data/pipeline_flow.md`.

## Структура репозитория

```
backend/
  contracts/          — контракты Kafka-событий и топиков
  infra/               — SQL-схемы, скрипты инициализации Kafka/S3/Postgres/ClickHouse
  deploy/helm/         — Helm-чарты для k8s
  microservices/       — исходники всех сервисов
  tools/test_producer/ — тестовый продюсер для e2e-проверки
  docker-compose.yml   — локальный запуск всего стека
frontend/               — React-приложение (dashboard, explorer, top-errors, admin)
data/                   — проектная документация и дизайн-документы
```
