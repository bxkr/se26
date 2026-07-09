# Event contracts

`topics.json` — маппинг логического имени темы на реальное имя Kafka-топика (создаются `infra/kafka/create_topics.sh`). `events/*.example.json` — пример payload'а для каждого `event_type`.

## Конвенция конверта

Каждое событие обязано содержать:

- `event_id` (UUID) — идентификатор конкретного события.
- `trace_id` (UUID) — сквозной идентификатор исходного запроса/цепочки; пробрасывается без изменений через все хопы пайплайна (need_info → raw.created → dm.ready/pipeline.failed).
- `event_type` — строка, совпадающая с именем топика (`weather.clean.created` и т.д.).
- `schema_version` (int) — версия схемы payload'а, сейчас у всех событий `1`.
- `created_at` — ISO8601 UTC, суффикс `Z`.

Остальные поля — специфичны для `event_type`, см. соответствующий `events/*.example.json`.

## `dataset_type`

`weather.dm.ready` несёт поле `dataset_type` (`"actual"` | `"forecast"`) — дискриминатор источника/цели в DAG `dm_pipeline`/Spark-джобе. Он не приходит отдельным полем во входном событии — `dm_trigger` подписан на два топика, `weather.actual.raw.created` и `weather.forecast.raw.created`, и определяет `dataset_type` по тому, из какого топика пришёл манифест: `actual` читает соответствующие `object_keys` (`actual/date=...json`) из S3 и пишет в `raw_weather_events`/`ods_daily_weather`/`dm_fct_daily_weather`, `forecast` — читает `forecast/date=...json` и пишет в `raw_forecast_events`/`ods_daily_forecast`/`dm_fct_daily_forecast`. После каждой DM-записи (в любой ветке) пересчитывается витрина `weather.dm_fct_forecast_error` (join `dm_fct_daily_weather`×`dm_fct_daily_forecast` по `(wmo_index, day)`).

**Один DAG-ран на манифест, не на день**: `dm_trigger` триггерит ровно один Airflow DAG-ран на манифест-событие (`weather.actual.raw.created`/`weather.forecast.raw.created`), передавая весь `date_from`/`date_to` из манифеста. Spark-джоба сама конструирует список S3-ключей на каждый день диапазона (`{prefix}/date=<day>.json`, детерминированно из `dataset_type`) и читает их одним batch-чтением, вместо того чтобы запускать отдельный JVM/DAG-ран на каждый день. Соответственно `weather.dm.ready` несёт `date_from`/`date_to` (а не `observation_date`) — одно событие означает "весь диапазон трейса обработан", не "один день".

`weather.clean.created` — **retired**, из активного потока выведен (раньше публиковался `etl_service`, которого больше нет; ничего его больше не публикует и не потребляет).

## `weather.pipeline.failed`

Единый контракт ошибки, публикуется любым шагом пайплайна на терминальный сбой (в т.ч. «источника нет данных за период» — не должно проглатываться тихим `ack`). Поля сверх конверта: `stage` (`fetch|etl|dm_trigger|dm`), `source_name` (сервис-источник), `reason` (короткий машиночитаемый код), `details` (человекочитаемое описание).

## Дизайн-документ

Полная схема сквозного пайплайна и статус реализации каждого шага — `data/pipeline_flow.md`.
