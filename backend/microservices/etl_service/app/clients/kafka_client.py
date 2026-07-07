from __future__ import annotations

import os
from typing import Any, Callable

from kafka import KafkaConsumer


class KafkaConsumerClient:
    def __init__(
        self,
        *,
        bootstrap_servers: list[str],
        topic: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
        logger: Any | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._logger = logger
        self._consumer: KafkaConsumer | None = None
        self._running = False

    @classmethod
    def from_env(cls, *, logger: Any | None = None) -> "KafkaConsumerClient":
        bootstrap_servers_raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        bootstrap_servers = [item.strip() for item in bootstrap_servers_raw.split(",") if item.strip()]

        return cls(
            bootstrap_servers=bootstrap_servers,
            topic=os.getenv("KAFKA_TOPIC", "weather.actual.raw.created"),
            group_id=os.getenv("KAFKA_GROUP_ID", "etl-service"),
            auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
            logger=logger,
        )

    def start(self) -> None:
        if self._consumer is not None:
            return

        self._consumer = KafkaConsumer(
            self._topic,
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
            topic=self._topic,
            group_id=self._group_id,
            bootstrap_servers=",".join(self._bootstrap_servers),
        )

    def consume_forever(self, handler: Callable[[bytes], Any]) -> None:
        if self._consumer is None:
            self.start()

        assert self._consumer is not None

        self._running = True

        while self._running:
            for message in self._consumer:
                if not self._running:
                    break

                try:
                    self._log_info(
                        "kafka message received",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        key=message.key,
                    )

                    handler(message.value)

                    self._consumer.commit()

                    self._log_info(
                        "kafka message committed",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                    )
                except Exception as exc:
                    self._log_error(
                        "kafka message processing failed",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(exc),
                    )
                    raise

    def stop(self) -> None:
        self._running = False

        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

        self._log_info("kafka consumer stopped", topic=self._topic)

    def _log_info(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "info"):
            self._logger.info(message, **kwargs)

    def _log_error(self, message: str, **kwargs: Any) -> None:
        if self._logger and hasattr(self._logger, "error"):
            self._logger.error(message, **kwargs)