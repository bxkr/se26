# Как front_api подключается к analytics_api

Контракт между аналитикой и фронтом зафиксирован в `data/analytics_front_contract.md` (6 эндпоинтов, формат запросов/ответов, статус-коды) — этот документ его не дублирует, а описывает то, что контракт не покрывает: где сервис живёт, как к нему реально подключиться, как устроена асинхронная модель под капотом, и на что рассчитывать по срокам ответа. Общая архитектура пайплайна — `data/pipeline_flow.md`.

## Что уже работает

`analytics_api` задеплоен на k8s-кластере (namespace `dm-pipeline`), реализует все 6 эндпоинтов контракта поверх `weather.dm_fct_forecast_error` в ClickHouse. Синхронные ответы (`200`) — когда данные уже есть; асинхронные (`202` + `request_id` → поллинг/SSE) — когда чего-то не хватает и запущен дозапрос через Kafka.

```
front_api ──HTTP──▶ analytics_api ──ClickHouse read──▶ (данные уже есть) ──▶ 200
                                  └─недостающие дни──▶ weather.need_info (Kafka)
                                                          → historical_fetcher/ForecastFetcher → ... → weather.dm.ready
                                                        ◀── analytics_api дослушивает и обновляет request_id ──┘
front_api ──GET /requests/{id}──▶ analytics_api (Redis)  либо  ──GET /requests/{id}/stream──▶ SSE
```

## 1. Адрес сервиса

Внутри кластера (namespace `dm-pipeline`, где, по-видимому, будет жить и `front_api`):

```
http://analytics-api:8000
```

Порт `8000`, без auth (dev-grade стенд, как и весь остальной пайплайн). Health-check — `GET /analytics-api:8000/healthz` → `{"status": "ok"}`.

Снаружи кластера (локальная разработка `front_api` без деплоя в k8s):

```bash
kubectl port-forward -n dm-pipeline svc/analytics-api 8010:8000
```

После этого сервис доступен на `http://localhost:8010`.

## 2. Эндпоинты (см. `data/analytics_front_contract.md` за полным описанием полей)

| Метод + путь | Синхронный или асинхронный |
|---|---|
| `POST /regions/forecast-errors` | `200` сразу, если данные по **всем** запрошенным регионам/дням уже есть; иначе `202` |
| `POST /stations/forecast-errors` | то же самое, по списку станций |
| `POST /errors/top` | **всегда `200`** — без фильтра по станциям/регионам нечего дозапрашивать, читает то, что уже в ClickHouse |
| `POST /metrics/model` | **всегда `200`**, та же причина |
| `GET /requests/{requestId}` | поллинг статуса асинхронного запроса |
| `GET /requests/{requestId}/stream` | SSE-альтернатива поллингу, тот же статус в реальном времени |

`station_id` в контракте — это `wmo_index` напрямую (не отдельная система идентификаторов); список станций внутри региона резолвится через уже задеплоенный `regions-api` (`GET http://regions-api:8000/regions/{region_id}/wmo-indexes`), `front_api` в этот процесс не вовлечён.

## 3. Как устроена асинхронность (что происходит за `202`)

1. `analytics_api` проверяет ClickHouse **по дням**: день считается «закрытым» только если данные есть **по всем** запрошенным станциям на эту дату (строгое покрытие, не «хоть что-то»).
2. Недостающие дни группируются в непрерывные диапазоны; на каждый диапазон публикуются **два** события `weather.need_info` в Kafka — `dataset_type: "actual"` и `dataset_type: "forecast"` (`dm_fct_forecast_error` — это join actual×forecast, заранее не известно, какая сторона отсутствует).
3. `analytics_api` слушает `weather.dm.ready`/`weather.pipeline.failed` и переводит `request_id` в `ready`/`failed`, когда дождался ответа по всем опубликованным событиям.
4. Состояние запроса и дедуп-локи (чтобы конкурентные одинаковые запросы не дублировали `weather.need_info`) хранятся в Redis — том же инстансе, что и `front_api` (см. п.5).

`ForecastFetcher` задеплоен и обрабатывает `weather.need_info{dataset_type:"forecast"}` по-настоящему: резолвит координаты станции через `regions-api`, тянет прогноз из Open-Meteo Historical Forecast API, пишет `forecast/date=...json` в S3 и публикует `weather.forecast.raw.created`. Обе стороны (`actual` и `forecast`) теперь реально дозапрашиваются и приходят — `202`-запрос доходит до `ready`, а не висит до таймаута. Проверено end-to-end (`weather.need_info` → S3 → `dm_trigger` → Airflow DAG → Spark → ClickHouse → `weather.dm.ready`).

`front_api` всё равно стоит закладывать таймаут ожидания на своей стороне не короче `ANALYTICS_REQUEST_TIMEOUT_SECONDS` (по умолчанию 600с/10 минут) — это по-прежнему рабочий сценарий: сбой внешнего API прогнозов, отсутствие координат станции в `regions-api`, сетевые проблемы и т.п. приведут к тому же `pending` → `failed` по таймауту, просто это больше не гарантированный исход для любого forecast-запроса.

## 4. Формат ошибок

`400` — валидация запроса, тело **без** обёртки `detail` (важно: FastAPI по умолчанию обернул бы в `{"detail": ...}`, здесь это явно исправлено кастомным exception handler'ом под форму контракта):

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Field 'stations' is required"}}
```

`404` на `GET /requests/{requestId}` с неизвестным `request_id`:

```json
{"error": {"code": "NOT_FOUND", "message": "unknown request_id"}}
```

## 5. Общий Redis — как его делить с `analytics_api`

Redis (`redis:6379` внутри кластера, без пароля) уже используется `analytics_api` под собственное состояние. Ключи `analytics_api` — зарезервированные префиксы, `front_api` не должен их трогать/переиспользовать:

- `req:{request_id}` — состояние запроса (`status`, `result`, `error_message`, ...), TTL 1 час.
- `lock:{dataset_type}:{wmo_index}:{day}` — дедуп-локи на дозапрос через Kafka.
- `waiters:{trace_id}` — какие `request_id` ждут конкретное Kafka-событие.
- `pending_requests` — SET активных pending-запросов (для sweep-таска по таймаутам).

`front_api` может использовать тот же Redis-инстанс под свои нужды (сессии, кэш и т.п.) — просто с другими префиксами ключей, коллизий не будет. Никакого общего протокола/шэринга данных между `analytics_api` и `front_api` через Redis не предполагается — только раздельные namespace'ы в одном инстансе, чтобы не разворачивать второй Redis ради экономии ресурсов на некрупном кластере.

## 6. Пример: полный цикл на стороне front_api

```python
import asyncio

import httpx

BASE_URL = "http://analytics-api:8000"

async def get_station_errors(client: httpx.AsyncClient, station: str, date_from: str, date_to: str) -> dict:
    resp = await client.post(
        f"{BASE_URL}/stations/forecast-errors",
        json={"from": date_from, "to": date_to, "stations": [station]},
    )
    body = resp.json()

    if body["status"] == "ready":
        return body["data"]

    request_id = body["request_id"]
    while True:
        status_resp = await client.get(f"{BASE_URL}/requests/{request_id}")
        status_body = status_resp.json()
        if status_body["status"] == "ready":
            # данные теперь есть в ClickHouse — перезапросить тот же эндпоинт,
            # analytics_api сам отдаст 200 (промежуточный результат в
            # status_body не хранит rows, GET /requests/{id} — это только статус)
            resp = await client.post(
                f"{BASE_URL}/stations/forecast-errors",
                json={"from": date_from, "to": date_to, "stations": [station]},
            )
            return resp.json()["data"]
        if status_body["status"] == "failed":
            raise RuntimeError(status_body["error_message"])
        await asyncio.sleep(2)
```

Либо то же самое через SSE вместо ручного поллинга — `GET /requests/{request_id}/stream`, кадры `event: status|ready|failed`, формат — см. `data/analytics_front_contract.md`.

## 7. Где что лежит в репозитории

| Что | Путь |
|---|---|
| `analytics_api` (код) | `backend/microservices/analytics_api/` |
| Контракт с фронтом | `data/analytics_front_contract.md` |
| `regions-api` (резолв региона в список станций) | `backend/microservices/regions_api/` |
| Helm-чарты | `backend/deploy/helm/{analytics-api,redis,regions-api}` |
| Схема ClickHouse (`dm_fct_forecast_error` и остальное) | `backend/infra/clickhouse/schema.sql` |
| Контракты Kafka-событий (`weather.need_info`, `weather.dm.ready`, `weather.pipeline.failed`) | `backend/contracts/` |

## 8. Известные ограничения (осознанно, не баги)

- Обе стороны (`actual` через `historical_fetcher`, `forecast` через `ForecastFetcher`) дозапрашиваются по-настоящему и доходят до `ready`. Таймаут по-прежнему возможен как исход сбоя (внешний API недоступен, нет координат станции и т.п.), но не как гарантированное поведение для forecast-стороны.
- `/errors/top` и `/metrics/model` никогда не запускают дозапрос — если нужных данных нет вообще ни по одной станции, они просто вернут пустой/нулевой результат синхронно, а не `202`.
- Дедуп через Redis-лок — по первому дню диапазона, не по всему диапазону целиком (упрощение, безопасное за счёт идемпотентности `historical_fetcher` при повторном дозапросе того же диапазона).
- Нет `.sourcecraft/ci.yaml` — сборка/деплой вручную (`docker buildx build --platform linux/amd64 ... --push` + `helm upgrade --install`), как и у остальных сервисов в этом пайплайне.
