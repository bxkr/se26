from __future__ import annotations

import json
import os
from typing import Any

from kafka import KafkaProducer

_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        bootstrap_servers_raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        bootstrap_servers = [s.strip() for s in bootstrap_servers_raw.split(",") if s.strip()]
        _producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
            retries=5,
        )
    return _producer


def publish_event(topic: str, event: dict[str, Any]) -> None:
    producer = _get_producer()
    future = producer.send(topic, value=event)
    future.get(timeout=30)
    producer.flush()
