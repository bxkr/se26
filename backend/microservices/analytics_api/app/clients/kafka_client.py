from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable

from kafka import KafkaConsumer, KafkaProducer


class KafkaConsumerClient:
    def __init__(
        self,
        *,
        bootstrap_servers: list[str],
        topics: list[str],
        group_id: str,
        auto_offset_reset: str = "earliest",
        logger: Any | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topics = topics
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._logger = logger
        self._consumer: KafkaConsumer | None = None
        self._running = False

    @classmethod
    def from_env(cls, *, logger: Any | None = None) -> "KafkaConsumerClient":
        bootstrap_servers_raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        bootstrap_servers = [item.strip() for item in bootstrap_servers_raw.split(",") if item.strip()]

        topics_raw = os.getenv("KAFKA_TOPICS", "weather.dm.ready,weather.pipeline.failed")
        topics = [item.strip() for item in topics_raw.split(",") if item.strip()]

        return cls(
            bootstrap_servers=bootstrap_servers,
            topics=topics,
            group_id=os.getenv("KAFKA_GROUP_ID", "analytics-api"),
            auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
            logger=logger,
        )

    def start(self) -> None:
        if self._consumer is not None:
            return

        self._consumer = KafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            enable_auto_commit=False,
            auto_offset_reset=self._auto_offset_reset,
            value_deserializer=lambda value: value,
            key_deserializer=lambda value: value.decode("utf-8") if value else None,
            consumer_timeout_ms=1000,
        )

        self._log_info(
            "kafka consumer started",
            topics=",".join(self._topics),
            group_id=self._group_id,
            bootstrap_servers=",".join(self._bootstrap_servers),
        )

    def consume_forever(self, handler: Callable[[bytes, str], Any]) -> None:
        if self._consumer is None:
            self.start()

        assert self._consumer is not None

        self._running = True

        while self._running:
            for message in self._consumer:
                if not self._running:
                    break

                self._log_info(
                    "kafka message received",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    key=message.key,
                )

                # The handler is responsible for swallowing its own
                # exceptions — one bad dm.ready/pipeline.failed message must
                # not crash the consumer loop for every other request in flight.
                handler(message.value, message.topic)

                self._consumer.commit()

                self._log_info(
                    "kafka message committed",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                )

    def stop(self) -> None:
        self._running = False

        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

        self._log_info("kafka consumer stopped", topics=",".join(self._topics))

    def _log_info(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "info"):
            self._logger.info(message, **kwargs)


class KafkaProducerClient:
    def __init__(self, *, bootstrap_servers: list[str], logger: Any | None = None) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._logger = logger
        self._producer: KafkaProducer | None = None

    @classmethod
    def from_env(cls, *, logger: Any | None = None) -> "KafkaProducerClient":
        bootstrap_servers_raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        bootstrap_servers = [item.strip() for item in bootstrap_servers_raw.split(",") if item.strip()]
        return cls(bootstrap_servers=bootstrap_servers, logger=logger)

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
                retries=5,
            )
        return self._producer

    def send(self, topic: str, event: dict[str, Any]) -> None:
        producer = self._get_producer()
        future = producer.send(topic, value=event)
        metadata = future.get(timeout=30)
        producer.flush()

        self._log_info(
            "event published",
            topic=metadata.topic,
            partition=metadata.partition,
            offset=metadata.offset,
            event_id=event.get("event_id"),
            trace_id=event.get("trace_id"),
        )

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()
            self._producer = None

    def _log_info(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "info"):
            self._logger.info(message, **kwargs)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
