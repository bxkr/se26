from uuid import UUID
from redis import Redis
from app.models.raw_events import ActualRawEvent, ForecastRawEvent


DEFAULT_DEDUP_TTL_SECONDS = 24 * 60 * 60 
DEFAULT_LOCK_TTL_SECONDS = 60


def build_forecast_dedup_key(event_id: UUID | str) -> str:
    return f"dedup:forecast:{event_id}"


def build_actual_dedup_key(event_id: UUID | str) -> str:
    return f"dedup:actual:{event_id}"


def build_forecast_lock_key(event_id: UUID | str) -> str:
    return f"lock:forecast:{event_id}"


def build_actual_lock_key(event_id: UUID | str) -> str:
    return f"lock:actual:{event_id}"


def build_forecast_dedup_key_from_event(event: ForecastRawEvent) -> str:
    return build_forecast_dedup_key(event.event_id)


def build_actual_dedup_key_from_event(event: ActualRawEvent) -> str:
    return build_actual_dedup_key(event.event_id)


def build_forecast_lock_key_from_event(event: ForecastRawEvent) -> str:
    return build_forecast_lock_key(event.event_id)


def build_actual_lock_key_from_event(event: ActualRawEvent) -> str:
    return build_actual_lock_key(event.event_id)


def is_duplicate(redis_client: Redis, dedup_key: str) -> bool:
    """Проверяет, было ли событие уже обработано"""

    return redis_client.exists(dedup_key) == 1


def mark_processed(
    redis_client: Redis,
    dedup_key: str,
    ttl_seconds: int = DEFAULT_DEDUP_TTL_SECONDS,
) -> None:
    """Помечает событие как обработанное на заданный TTL"""

    redis_client.set(dedup_key, "1", ex=ttl_seconds)


def acquire_lock(
    redis_client: Redis,
    lock_key: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    """
    Пытается поставить lock.
    Возвращает True, если lock успешно взят.
    Возвращает False, если lock уже существует.
    """

    return bool(redis_client.set(lock_key, "1", ex=ttl_seconds, nx=True))


def release_lock(redis_client: Redis, lock_key: str) -> None:
    """Снимает lock"""

    redis_client.delete(lock_key)


def should_skip_forecast_event(redis_client: Redis, event: ForecastRawEvent) -> bool:
    """True, если forecast событие уже обрабатывалось"""

    dedup_key = build_forecast_dedup_key_from_event(event)
    return is_duplicate(redis_client, dedup_key)


def should_skip_actual_event(redis_client: Redis, event: ActualRawEvent) -> bool:
    """True, если actual событие уже обрабатывалось"""

    dedup_key = build_actual_dedup_key_from_event(event)
    return is_duplicate(redis_client, dedup_key)


def mark_forecast_processed(
    redis_client: Redis,
    event: ForecastRawEvent,
    ttl_seconds: int = DEFAULT_DEDUP_TTL_SECONDS,
) -> None:
    """Пометить forecast обработанным"""

    dedup_key = build_forecast_dedup_key_from_event(event)
    mark_processed(redis_client, dedup_key, ttl_seconds=ttl_seconds)


def mark_actual_processed(
    redis_client: Redis,
    event: ActualRawEvent,
    ttl_seconds: int = DEFAULT_DEDUP_TTL_SECONDS,
) -> None:
    """Пометить actual обработанным"""

    dedup_key = build_actual_dedup_key_from_event(event)
    mark_processed(redis_client, dedup_key, ttl_seconds=ttl_seconds)


def acquire_forecast_lock(
    redis_client: Redis,
    event: ForecastRawEvent,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    """Получает forecast lock"""

    lock_key = build_forecast_lock_key_from_event(event)
    return acquire_lock(redis_client, lock_key, ttl_seconds=ttl_seconds)


def acquire_actual_lock(
    redis_client: Redis,
    event: ActualRawEvent,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    """Получает actual lock"""

    lock_key = build_actual_lock_key_from_event(event)
    return acquire_lock(redis_client, lock_key, ttl_seconds=ttl_seconds)


def release_forecast_lock(redis_client: Redis, event: ForecastRawEvent) -> None:
    """Снимает forecast lock"""

    lock_key = build_forecast_lock_key_from_event(event)
    release_lock(redis_client, lock_key)


def release_actual_lock(redis_client: Redis, event: ActualRawEvent) -> None:
    """Снимает actual lock"""

    lock_key = build_actual_lock_key_from_event(event)
    release_lock(redis_client, lock_key)
