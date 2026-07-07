# Карта слоёв DWH — шаблон (заполнить на семинаре)

**Команда:** Архитекторы  
**Дата:** 2026-07-06

| Слой | Таблица / объект               | Комментарий                          | Гранулярность                               | Источник                            | Потребитель                                         | Зачем слой?                              |
|------|--------------------------------|--------------------------------------|---------------------------------------------|-------------------------------------|-----------------------------------------------------|------------------------------------------|
| RAW  | raw.telemetry_events           | События телеметрии (сырьё)           | событие                                     | L6 PostgreSQL                       | ods.ref_metric, ods.telemetry, ods.station_provider | JSON as-is с intake                      |
| RAW  | raw.forecast_events            | События прогнозов (сырьё)            | событие                                     | L6 PostgreSQL                       | ods.ref_provider, ods.forecasts                     | JSON as-is с сервиса прогнозов           |
| RAW  | raw.stations_snapshot          | События справочника станций          | событие                                     | L6 PostgreSQL                       | ods.ref_region, ods.stations                        | Master data batch                        |
| ODS  | ods.ref_region                 | Справочник регионов                  | **region_code** ↔ region_name               | raw.stations_snapshot               | dds.dim_region                                      | соотношение кода и названия региона      |
| ODS  | ods.ref_provider               | Справочник провайдеров прогноза      | **provider_code** ↔ provider_name           | raw.stations_snapshot               | dds.dim_provider                                    | соотношнеие кода и названия провайдера   |
| ODS  | ods.ref_metric                 | Справочник метрик                    | подробности метрики                         | raw.telemetry_events                | dds.dim_metric                                      | описание метрики                         |
| ODS  | ods.stations                   | Станции (staging)                    | связь "станция ↔ регион"                    | raw.stations_snapshot               | dds.dim_station                                     | соотношение станции и региона            |
| ODS  | ods.station_provider           | Покрытие                             | связь "станция ↔ провайдер"                 | raw.telemetry_events                | dds.dim_station                                     | соотнощение станции и провайдера         |
| ODS  | ods.telemetry                  | Факты измерений                      | объект иземерения                           | raw.telemetry_events                | dds.fct_measurement, dds.fct_forecast_error         | объекты измерений                        |
| ODS  | ods.forecasts                  | Факты прогнозов                      | объект прогноза                             | raw.forecast_events                 | dds.fct_forecast, dds.fct_forecast_error            | объекты прогноза                         |
| DDS  | dds.dim_region                 | Измерение «регион»                   | **region_code** ↔ region_name               | ods.ref_region                      | dm.dim_region                                       | описание региона                         |
| DDS  | dds.dim_station                | Измерение «метеостанция»             | **station_id** ↔ region_code, provider_code | ods.stations + ods.station_provider | dm.dim_station                                      | описание станции                         |
| DDS  | dds.dim_provider               | Измерение «провайдер прогноза»       | **provider_code** ↔ provider_name           | ods.ref_provider                    | dm.dim_provider                                     | описание провайдера                      |
| DDS  | dds.dim_metric                 | Измерение «метрика»                  | подробности метрики                         | ods.ref_metric                      | dm.dim_metric                                       | описание метрики                         |
| DDS  | dds.fct_measurement            | Факт «измерение с датчика»           | объект иземерения                           | ods.telemetry                       | -                                                   | объекты измерений                        |
| DDS  | dds.fct_forecast               | Факт «прогноз»                       | объект прогноза                             | ods.forecasts                       | -                                                   | объекты прогноза                         |
| DDS  | dds.fct_forecast_error         | Факт «ошибка прогноза»               | разница измерения и прогноза                | ods.telemetry + ods.forecasts       | dm.fct_forecast_accuracy_daily                      | ошибка, которую представляем в DM        |
| DM   | dm.dim_region                  | Измерение витрины «регион»           | **region_code** ↔ region_name               | dds.dim_region                      | BI                                                  | отображает регион                        |
| DM   | dm.dim_station                 | Измерение витрины «станция»          | **station_id** ↔ region_code, provider_code | dds.dim_station                     | BI                                                  | отображает информацию о станции          |
| DM   | dm.dim_provider                | Измерение витрины «провайдер»        | **provider_code** ↔ provider_name           | dds.dim_provider                    | BI                                                  | отображает информацию о провайдере       |
| DM   | dm.dim_metric                  | Измерение витрины «метрика»          | подробности метрики                         | dds.dim_metric                      | BI                                                  | отображает информацию о метрике          |
| DM   | dm.dim_day                     | Измерение витрины «календарный день» | календарный день                            | dds.fct_forecast_error              | BI                                                  | отображает календарный день              |
| DM   | dm.fct_forecast_accuracy_daily | Факт «точность прогноза за сутки»    | точность прогноза за данные сутки           | dds.fct_forecast_error              | BI                                                  | отображает точность в определенные сутки |

## Вопросы для заполнения

1. Зачем **`ods.station_provider`**, если провайдер уже в `forecasts`?
2. Чем **`dds.fct_measurement`** отличается от **`dds.fct_forecast_error`**?
3. Зачем **`dm.dim_region`**, если region есть в `dm.dim_station`?
4. Где считается **`coverage_pct`** — DDS или DM?
5. Может ли **дашборд** JOIN'ить `dds.*` напрямую?
