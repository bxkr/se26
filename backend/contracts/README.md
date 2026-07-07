# Event contracts

`topics.json` — маппинг логического имени темы на реальное имя Kafka-топика (создаются `infra/kafka/create_topics.sh`). `events/*.example.json` — пример payload'а для каждого `event_type`.

## Конвенция конверта

Каждое событие обязано содержать:

- `event_id` (UUID) — идентификатор конкретного события.
- `trace_id` (UUID) — сквозной идентификатор исходного запроса/цепочки; пробрасывается без изменений через все хопы пайплайна (need_info → raw.created → clean.created → dm.ready/pipeline.failed).
- `event_type` — строка, совпадающая с именем топика (`weather.clean.created` и т.д.).
- `schema_version` (int) — версия схемы payload'а, сейчас у всех событий `1`.
- `created_at` — ISO8601 UTC, суффикс `Z`.

Остальные поля — специфичны для `event_type`, см. соответствующий `events/*.example.json`.

## `dataset_type`

`weather.clean.created` и `weather.dm.ready` несут поле `dataset_type` (`"actual"` | `"forecast"`) — это не просто описательное поле, а дискриминатор источника/цели в `dm_trigger`/DAG `dm_pipeline`/Spark-джобе: `actual` читает `weather_actual` и пишет в `raw_weather_events`/`ods_daily_weather`/`dm_fct_daily_weather`, `forecast` — читает `weather_forecast` и пишет в `raw_forecast_events`/`ods_daily_forecast`/`dm_fct_daily_forecast`. После каждой DM-записи (в любой ветке) пересчитывается витрина `weather.dm_fct_forecast_error` (join `dm_fct_daily_weather`×`dm_fct_daily_forecast` по `(wmo_index, day)`). Отсутствие `dataset_type` в событии трактуется как `"actual"` (обратная совместимость).

## `weather.pipeline.failed`

Единый контракт ошибки, публикуется любым шагом пайплайна на терминальный сбой (в т.ч. «источника нет данных за период» — не должно проглатываться тихим `ack`). Поля сверх конверта: `stage` (`fetch|etl|dm_trigger|dm`), `source_name` (сервис-источник), `reason` (короткий машиночитаемый код), `details` (человекочитаемое описание).

## Дизайн-документ

Полная схема сквозного пайплайна и статус реализации каждого шага — `data/pipeline_flow.md`.
