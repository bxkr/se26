# Как React-фронт подключается к front_api

`front_api` — единственный backend, с которым говорит React. Он сам обслуживает auth/админку и прозрачно проксирует дашборд-эндпоинты в `analytics_api` (с кэшем в Redis) — фронту не нужно ничего знать про `analytics_api`, регионы/станции или Kafka-асинхронность напрямую, всё это спрятано за `front_api`.

Контракт `analytics_api` ↔ `front_api` описан в `data/analytics_front_contract.md` и `data/analytics_front_integration.md` — этот документ его не дублирует, а описывает то, что видно только с внешней стороны, у React.

## 1. Адрес сервиса

Снаружи (боевой домен, TLS в процессе выпуска через Yandex Certificate Manager):

```
https://api-se26.bxkr.org
```

Пока сертификат не выпущен — доступен по HTTP на том же домене. Локальная разработка через `docker-compose`:

```
http://localhost:8003
```

Health-check — `GET /healthz` → `{"status": "ok"}`.

## 2. Аутентификация

JWT access+refresh в httpOnly cookie — фронт **не хранит и не читает токены сам**, только шлёт запросы с `credentials: "include"` (fetch) / `withCredentials: true` (axios), браузер сам прикладывает cookie.

| Метод + путь | Назначение |
|---|---|
| `POST /auth/login` | `{"username", "password"}` → `200 {"user": {"id","username","role"}}`, ставит cookies `access_token`/`refresh_token` |
| `POST /auth/refresh` | Обновляет пару cookies по `refresh_token` (ротация — старый инвалидируется). Дергать при `401` на любом защищённом запросе, затем повторить исходный запрос |
| `POST /auth/logout` | Чистит cookies, отзывает refresh-токен |
| `GET /auth/me` | Текущий пользователь по `access_token`. Использовать при старте приложения, чтобы понять — показывать лендинг или дашборд |

**Access-токен живёт 15 минут** (`FRONT_API_ACCESS_TOKEN_TTL_SECONDS`, по умолчанию 900) — фронту нужен общий interceptor: на `401` от любого запроса (кроме самого `/auth/*`) прозрачно дернуть `/auth/refresh` и повторить оригинальный запрос один раз; если `/auth/refresh` тоже вернул `401` — сессия истекла, редирект на лендинг.

**Демо-аккаунт**: обычный пользователь (роль `user`), логин как все — кнопка "Demo" на лендинге просто вызывает `POST /auth/login` с зашитыми демо-кредами (не отдельный флоу, не отдельный эндпоинт).

Роль пользователя (`user`/`admin`) приходит в `GET /auth/me` — на неё завязана видимость админ-раздела в UI (это только UI-уровень, сервер сам отдаёт `403` на `/admin/*` не-админам, так что дублирующая проверка на фронте — для UX, не для безопасности).

## 3. Дашборд-эндпоинты (прокси к analytics_api)

Пути один в один повторяют `data/analytics_front_contract.md` — `front_api` их напрямую проксирует, добавляя кэш в Redis для успешных ответов:

| Путь | Кэшируется? |
|---|---|
| `POST /regions/forecast-errors` | да, если `status:"ready"` |
| `POST /stations/forecast-errors` | да, если `status:"ready"` |
| `POST /errors/top` | да |
| `POST /metrics/model` | да |
| `GET /requests/{requestId}` | нет (поллинг, всегда свежий) |
| `GET /requests/{requestId}/stream` | нет (SSE passthrough) |

Все требуют авторизации (любая роль — `user` или `admin`).

**Асинхронность видна и фронту**: любой из первых четырёх POST-запросов может вернуть либо `200 {"status":"ready", "data":{...}}` сразу, либо `202 {"status":"pending", "request_id":"..."}`, если часть данных нужно дозапросить у источника. В последнем случае — либо поллинг `GET /requests/{request_id}` каждые 1-2 секунды, либо `GET /requests/{request_id}/stream` (SSE, события `status`/`ready`/`failed`); как только статус `ready`, **повторить исходный POST** — данные уже будут в кэше/ClickHouse, и `front_api` в этот раз ответит `200` сразу. Ответ `GET /requests/{id}` не содержит сами данные, только статус.

Учитывай два жёстких предела по покрытию данных источниками (оба уже зашиты в фронте как `REQUEST_MIN_DATE`/`REQUEST_MAX_DATE`, `frontend/src/lib/constants.ts`):
- **Нижняя граница `2022-01-01`**: у прогнозной стороны (`dataset_type:"forecast"`) реальные данные от Open-Meteo Historical Forecast API доступны примерно с 2021 года — запросы на более ранние периоды физически не могут "дозаполниться" и уйдут в `failed` по таймауту (10 минут по умолчанию).
- **Верхняя граница `2025-03-31`**: у actual-стороны (`historical_fetcher` → `historical-se26.bxkr.org`) источник отдаёт `null` по всем станциям начиная с 2025-04-01 (проверено прямым запросом к API) — запрос на более поздний период вернёт `200 ready`, но со всеми error-метриками `null`, что выглядит как баг, а на деле просто отсутствие данных у источника.

Оба предела — свойство внешних источников, не баг пайплайна; UI должен либо не давать выбрать даты вне этого диапазона (как сейчас), либо явно объяснять, почему за его пределами данных не будет.

## 4. Админ-эндпоинты (только роль `admin`)

Все под `/admin/users`, `403` для роли `user`:

| Метод + путь | Действие |
|---|---|
| `GET /admin/users` | список всех пользователей |
| `POST /admin/users` | `{"username","password","role"}` → создать |
| `PATCH /admin/users/{id}` | `{"role"?, "is_active"?}` → частичное обновление |
| `DELETE /admin/users/{id}` | удалить |
| `POST /admin/users/{id}/reset-password` | `{"new_password"}` → сбросить пароль |

## 5. Формат ошибок

Плоский, без `detail`-обёртки — единый по всему пайплайну:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Field 'stations' is required"}}
```

Коды: `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409, например занятый username при создании пользователя), `RATE_LIMITED` (429, см. ниже).

### Защита от вандальных запросов

- **Лимит диапазона дат**: `from`/`to` в `/regions/forecast-errors`, `/stations/forecast-errors`, `/errors/top`, `/metrics/model` не могут охватывать больше `FRONT_API_MAX_REQUEST_RANGE_DAYS` дней (по умолчанию 180) — превышение отдаёт `400 VALIDATION_ERROR` ещё на уровне `front_api`, до похода в `analytics_api`/ClickHouse/Kafka-дозапрос. Отдельный, более широкий потолок `ANALYTICS_MAX_REQUEST_DAYS` (365) у `analytics_api` — вторая линия защиты, не основная.
- **Rate limit**: общий лимит `FRONT_API_RATE_LIMIT_REQUESTS` запросов за `FRONT_API_RATE_LIMIT_WINDOW_SECONDS` (по умолчанию 60/60с) на весь API, ключ — `user_id` после логина, иначе IP (`X-Forwarded-For`, если есть, иначе `request.client.host`). У `POST /auth/login` — отдельный, более жёсткий лимит по IP: `FRONT_API_LOGIN_RATE_LIMIT_REQUESTS`/`FRONT_API_LOGIN_RATE_LIMIT_WINDOW_SECONDS` (по умолчанию 10/300с), защита от брутфорса пароля ещё до появления сессии. Превышение любого из лимитов — `429 RATE_LIMITED`; фронту стоит показывать сообщение и не ретраить автоматически (никакого `Retry-After` пока не отдаётся).

## 6. CORS

`front_api` шлёт `Access-Control-Allow-Credentials: true` и явный список origin'ов (`FRONT_API_CORS_ORIGINS`, сейчас `http://localhost:3000` — плейсхолдер под локальную разработку React). **Когда определится боевой домен фронта — его нужно будет добавить в `FRONT_API_CORS_ORIGINS`** (через Helm `values.yaml` чарта `front-api`), иначе браузер будет молча резать все запросы с боевого домена на `api-se26.bxkr.org`.

## 7. Пример: логин + дашборд-запрос с обработкой 202

```javascript
const BASE_URL = "https://api-se26.bxkr.org";

async function apiFetch(path, options = {}) {
  const resp = await fetch(BASE_URL + path, { ...options, credentials: "include" });
  if (resp.status === 401 && path !== "/auth/refresh") {
    const refreshed = await fetch(BASE_URL + "/auth/refresh", { method: "POST", credentials: "include" });
    if (refreshed.ok) return apiFetch(path, options); // повтор один раз
  }
  return resp;
}

async function login(username, password) {
  const resp = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) throw new Error((await resp.json()).error.message);
  return (await resp.json()).user;
}

async function getStationErrors(stations, from, to) {
  const post = () =>
    apiFetch("/stations/forecast-errors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from, to, stations }),
    }).then((r) => r.json());

  let body = await post();
  if (body.status === "ready") return body.data;

  const requestId = body.request_id;
  while (true) {
    await new Promise((r) => setTimeout(r, 2000));
    const status = await apiFetch(`/requests/${requestId}`).then((r) => r.json());
    if (status.status === "ready") return (await post()).data;
    if (status.status === "failed") throw new Error(status.error_message);
  }
}
```

## 8. Где что лежит в репозитории

| Что | Путь |
|---|---|
| `front_api` (код) | `backend/microservices/front_api/` |
| Контракт `analytics_api` ↔ `front_api` | `data/analytics_front_contract.md`, `data/analytics_front_integration.md` |
| Helm-чарт | `backend/deploy/helm/front-api/` |
| Контракты Kafka-событий (для контекста, фронт их не видит напрямую) | `backend/contracts/` |

## 9. Дизайн

Design a web dashboard for WeatherPulse — a forecast-accuracy monitoring platform. The product ingests continuous weather sensor telemetry (real observations) and forecast data per weather station (identified by WMO index), compares them, and surfaces where forecasts were most wrong — by region, station, and time period. Users are meteorology/ops analysts monitoring model quality across many stations.

Style: clean, data-dense, professional analytics tool (think Grafana/Datadog/Linear), not playful. Dark mode as default with a light mode variant. A cool, restrained palette — one accent color for interactive elements/positive values, one clear warning/error color for high-error data points (this is a product about errors, so color-coding severity is central). Generous use of monospace font for numeric/station-ID data. Charts and tables are the heart of the product — prioritize legibility and scannability over decoration.

Screens to design:

1. Landing page (unauthenticated) — product pitch (1-2 sentences: "track where weather forecasts are wrong"), a primary "Sign in" button, and a secondary, visually distinct "Try demo account" button that logs straight in without a form.
2. Login page — username/password form, link back to landing, error state for invalid credentials.
3. Main dashboard (post-login) — top-level summary cards showing aggregate model metrics for a selected date range: rows count, temperature MAE, temperature bias, temp_min/temp_max MAE+bias, precipitation MAE+bias (8 numeric KPI tiles, each showing a value + a small trend/sparkline). A global date-range picker and region/station multi-select filter at the top, shared across the dashboard.
4. Top errors view — a sortable/filterable table of the worst-error rows (columns: WMO station index, date, temperature error, temp min/max error, precipitation error — signed and absolute variants), with a dropdown to choose which error metric to rank by, and a limit selector. Each row's error magnitude should be visually encoded (color intensity / bar) so the worst outliers pop out immediately. Clicking a row could open a detail drawer.
5. Region/station explorer — a map-or-list view letting the user pick a region (drill down to its stations) or search a station directly by WMO index, then see a time-series chart of forecast error over the selected date range for that station/region (line chart: actual vs forecast, and a separate error-over-time chart).
6. Async/loading state — since some queries can be slow (backend does a 202 pending → poll/SSE pattern while missing data is being fetched from upstream), design a clear "fetching missing data, this may take a few minutes" state with a progress indicator, and a graceful timeout/error state ("could not retrieve forecast data for this range").
7. Admin panel — a simple user management table (username, role badge user/admin, active/inactive toggle, created date) with actions to create a user (modal: username, password, role), reset a user's password, change role, deactivate/delete — only visible to admin-role users. Keep this screen plain/utilitarian, clearly a secondary "settings" area vs. the analytics-focused main screens.

Components needed in the design system: KPI/stat tile, data table with sortable columns and severity color-coding, line/time-series chart, date-range picker, multi-select filter chip group, async-loading banner/skeleton, role badge, modal form, top nav with user menu (shows current user + logout, demo-account users see a small "Demo mode" badge).

Design for desktop-first (this is an internal analytics tool) — **mobile/responsive layout is desired but not a priority**: keep the KPI tiles and table reasonably usable down to tablet width, but a fully-optimized phone layout can come later.
