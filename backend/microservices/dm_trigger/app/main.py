from __future__ import annotations

import logging
import os
import signal
from typing import Any

from app.clients.airflow_client import AirflowClient
from app.clients.kafka_client import KafkaConsumerClient, KafkaProducerClient
from app.handlers.raw_created_event_handler import RawCreatedEventHandler
from app.health import start_health_server


class AppLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(self._format(message, kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(self._format(message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(self._format(message, kwargs))

    def exception(self, message: str, **kwargs: Any) -> None:
        self._logger.exception(self._format(message, kwargs))

    @staticmethod
    def _format(message: str, kwargs: dict[str, Any]) -> str:
        if not kwargs:
            return message

        parts = [f"{key}={value}" for key, value in kwargs.items()]
        return f"{message} | " + " ".join(parts)


def configure_logging() -> AppLogger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    return AppLogger("dm_trigger")


def main() -> None:
    logger = configure_logging()

    start_health_server(port=int(os.getenv("HEALTH_PORT", "8000")))

    airflow_client = AirflowClient.from_env(logger=logger)
    producer = KafkaProducerClient.from_env(logger=logger)
    handler = RawCreatedEventHandler(airflow_client=airflow_client, producer=producer, logger=logger)
    kafka_client = KafkaConsumerClient.from_env(logger=logger)

    def shutdown_handler(signum: int, frame: Any) -> None:
        logger.info("shutdown signal received", signal=signum)
        kafka_client.stop()
        producer.close()

    signal.signal(signal.SIGINT, shutdown_handler)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        logger.info("dm_trigger service starting")
        kafka_client.consume_forever(handler.handle_message)
    except KeyboardInterrupt:
        logger.info("dm_trigger service interrupted by keyboard")
    except Exception as exc:
        logger.exception("dm_trigger service crashed", error=str(exc))
        raise
    finally:
        kafka_client.stop()
        producer.close()
        logger.info("dm_trigger service stopped")


if __name__ == "__main__":
    main()
