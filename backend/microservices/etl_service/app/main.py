from __future__ import annotations

import logging
import signal
from typing import Any

from app.clients.kafka_client import KafkaConsumerClient
from app.clients.postgres_client import PostgresClient
from app.clients.s3_client import S3Client
from app.handlers.raw_event_handler import RawEventHandler
from app.services.writer import WeatherActualWriter


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
    return AppLogger("etl_service")


def main() -> None:
    logger = configure_logging()

    s3_client = S3Client.from_env()
    postgres_client = PostgresClient.from_env()
    writer = WeatherActualWriter(postgres_client=postgres_client, logger=logger)
    handler = RawEventHandler(
        s3_client=s3_client,
        writer=writer,
        logger=logger,
    )
    kafka_client = KafkaConsumerClient.from_env(logger=logger)

    def shutdown_handler(signum: int, frame: Any) -> None:
        logger.info("shutdown signal received", signal=signum)
        kafka_client.stop()
        postgres_client.close()

    signal.signal(signal.SIGINT, shutdown_handler)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        logger.info("etl service starting")
        kafka_client.consume_forever(handler.handle_message)
    except KeyboardInterrupt:
        logger.info("etl service interrupted by keyboard")
    except Exception as exc:
        logger.exception("etl service crashed", error=str(exc))
        raise
    finally:
        kafka_client.stop()
        postgres_client.close()
        logger.info("etl service stopped")


if __name__ == "__main__":
    main()