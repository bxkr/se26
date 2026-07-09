

# 1) `POST /regions/forecast-errors`

**Назначение:** вернуть **все строки из таблицы** `weather.dm_fct_forecast_error`, которые относятся к переданным регионам.

**Важно:** фильтрация идёт по регионам, но в ответе возвращаем **именно строки таблицы**, без лишней аналитики.

### Request
```json
{
  "from": "2026-07-01",
  "to": "2026-07-07",
  "regions": ["region_77", "region_78"]
}
```

### Response `200`
```json
{
  "status": "ready",
  "data": {
    "rows": [
      {
        "wmo_index": "12345",
        "day": "2026-07-01",
        "temperature_error": -1.2,
        "temperature_abs_error": 1.2,
        "temp_min_error": -0.8,
        "temp_min_abs_error": 0.8,
        "temp_max_error": -1.7,
        "temp_max_abs_error": 1.7,
        "precipitation_mm_error": 0.4,
        "precipitation_mm_abs_error": 0.4,
        "ingested_at": "2026-07-08T10:00:00Z"
      },
      {
        "wmo_index": "12346",
        "day": "2026-07-01",
        "temperature_error": null,
        "temperature_abs_error": null,
        "temp_min_error": -0.3,
        "temp_min_abs_error": 0.3,
        "temp_max_error": 1.1,
        "temp_max_abs_error": 1.1,
        "precipitation_mm_error": 2.0,
        "precipitation_mm_abs_error": 2.0,
        "ingested_at": "2026-07-08T10:00:00Z"
      }
    ]
  }
}
```

### Response `202`
```json
{
  "status": "pending",
  "request_id": "req_regions_forecast_errors_001"
}
```

### Response `400`
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'regions' is required"
  }
}
```

---

# 2) `POST /stations/forecast-errors`

**Назначение:** вернуть **все строки из таблицы** `weather.dm_fct_forecast_error`, которые относятся к переданным станциям.

### Request
```json
{
  "from": "2026-07-01",
  "to": "2026-07-07",
  "stations": ["station_1001", "station_1002"]
}
```

### Response `200`
```json
{
  "status": "ready",
  "data": {
    "rows": [
      {
        "wmo_index": "12345",
        "day": "2026-07-01",
        "temperature_error": -1.2,
        "temperature_abs_error": 1.2,
        "temp_min_error": -0.8,
        "temp_min_abs_error": 0.8,
        "temp_max_error": -1.7,
        "temp_max_abs_error": 1.7,
        "precipitation_mm_error": 0.4,
        "precipitation_mm_abs_error": 0.4,
        "ingested_at": "2026-07-08T10:00:00Z"
      }
    ]
  }
}
```

### Response `202`
```json
{
  "status": "pending",
  "request_id": "req_stations_forecast_errors_001"
}
```

### Response `400`
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'stations' is required"
  }
}
```

---

# 3) `POST /errors/top`

**Назначение:** вернуть строки с **максимальными ошибками** по выбранному полю ошибки.

Это уже не агрегат “в вакууме”, а реально полезная штука:  
можно быстро смотреть, где были самые плохие прогнозы.

### Request
```json
{
  "from": "2026-07-01",
  "to": "2026-07-07",
  "metric": "temperature_abs_error",
  "limit": 100
}
```

### Допустимые `metric`
- `temperature_error`
- `temperature_abs_error`
- `temp_min_error`
- `temp_min_abs_error`
- `temp_max_error`
- `temp_max_abs_error`
- `precipitation_mm_error`
- `precipitation_mm_abs_error`

### Response `200`
```json
{
  "status": "ready",
  "data": {
    "metric": "temperature_abs_error",
    "rows": [
      {
        "wmo_index": "12345",
        "day": "2026-07-03",
        "temperature_error": 8.7,
        "temperature_abs_error": 8.7,
        "temp_min_error": 6.1,
        "temp_min_abs_error": 6.1,
        "temp_max_error": 9.0,
        "temp_max_abs_error": 9.0,
        "precipitation_mm_error": 0.0,
        "precipitation_mm_abs_error": 0.0,
        "ingested_at": "2026-07-08T10:00:00Z"
      }
    ]
  }
}
```

### Response `202`
```json
{
  "status": "pending",
  "request_id": "req_errors_top_001"
}
```

---

# 4) `POST /metrics/model`

**Назначение:** вернуть **общие агрегированные метрики по таблице** за период.

Это уже нормальный “summary”, который реально полезен, и при этом он простой.

### Request
```json
{
  "from": "2026-07-01",
  "to": "2026-07-07"
}
```

### Response `200`
```json
{
  "status": "ready",
  "data": {
    "rows_count": 125034,
    "temperature_mae": 1.82,
    "temperature_bias": -0.21,
    "temp_min_mae": 1.44,
    "temp_min_bias": -0.10,
    "temp_max_mae": 2.11,
    "temp_max_bias": -0.35,
    "precipitation_mm_mae": 0.73,
    "precipitation_mm_bias": 0.08
  }
}
```

### Response `202`
```json
{
  "status": "pending",
  "request_id": "req_metrics_model_001"
}
```

---

# 4b) `POST /metrics/model/daily`

**Назначение:** те же метрики, что в `/metrics/model`, но с разбивкой по дням — источник для трендового графика на дашборде. Добавлен позже основного контракта (не было в исходной спецификации), тот же request/response shape, что и `/metrics/model`, просто `data` — не один объект, а `{"rows": [...]}` по дням. Дни без данных в диапазоне просто отсутствуют в массиве (без заполнения нулями/`null`).

### Request
```json
{
  "from": "2026-07-01",
  "to": "2026-07-07"
}
```

### Response `200`
```json
{
  "status": "ready",
  "data": {
    "rows": [
      {
        "day": "2026-07-01",
        "rows_count": 17862,
        "temperature_mae": 1.75,
        "temperature_bias": -0.18,
        "temp_min_mae": 1.40,
        "temp_min_bias": -0.09,
        "temp_max_mae": 2.05,
        "temp_max_bias": -0.30,
        "precipitation_mm_mae": 0.70,
        "precipitation_mm_bias": 0.05
      }
    ]
  }
}
```

### Response `202`
Та же форма, что у `/metrics/model` — `{"status": "pending", "request_id": "..."}`.

---

# 5) `GET /requests/{requestId}`

**Назначение:** статус асинхронного запроса.

### Request
```json
{
  "requestId": "req_regions_forecast_errors_001"
}
```

### Response `200`
```json
{
  "request_id": "req_regions_forecast_errors_001",
  "status": "pending",
  "created_at": "2026-07-08T10:10:00Z",
  "updated_at": "2026-07-08T10:10:00Z",
  "error_message": null
}
```

### Response `200` ready
```json
{
  "request_id": "req_regions_forecast_errors_001",
  "status": "ready",
  "created_at": "2026-07-08T10:10:00Z",
  "updated_at": "2026-07-08T10:11:12Z",
  "error_message": null
}
```

### Response `200` failed
```json
{
  "request_id": "req_regions_forecast_errors_001",
  "status": "failed",
  "created_at": "2026-07-08T10:10:00Z",
  "updated_at": "2026-07-08T10:11:12Z",
  "error_message": "Upstream data preparation failed"
}
```

---

# 6) `GET /requests/{requestId}/stream`

**Назначение:** SSE-стрим по статусу запроса.

### Request
```json
{
  "requestId": "req_regions_forecast_errors_001"
}
```

### Response headers
```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### Event `pending`
```text
event: status
data: {"request_id":"req_regions_forecast_errors_001","status":"pending","updated_at":"2026-07-08T10:10:00Z"}
```

### Event `ready`
```text
event: ready
data: {"request_id":"req_regions_forecast_errors_001","status":"ready","updated_at":"2026-07-08T10:11:12Z"}
```

### Event `failed`
```text
event: failed
data: {"request_id":"req_regions_forecast_errors_001","status":"failed","updated_at":"2026-07-08T10:11:12Z","error_message":"Upstream data preparation failed"}
```

---

## Что по сути меняется

Теперь логика очень простая:

- **regions endpoint** → отдай строки таблицы по списку регионов
- **stations endpoint** → отдай строки таблицы по списку станций
- **top errors** → отдай самые плохие строки по выбранной метрике
- **model metrics** → отдай общие агрегаты
- **status / stream** → если запрос тяжёлый и асинхронный

---

## Важный момент по таблице

У тебя в `weather.dm_fct_forecast_error` **нет** полей:
- `region_id`
- `station_id`

Значит, если ты хочешь фильтровать по регионам и станциям, то backend всё равно будет делать **join / mapping** через справочник станций / регионов / `wmo_index`.

Но это **внутренняя логика backend**.  
В контракте это можно вообще не раздувать. Просто:

- на вход даём `regions` или `stations`
- на выходе получаем **строки из `dm_fct_forecast_error`**

Это как раз соответствует тому, что ты хочешь: **без аналитической мишуры**.

---

