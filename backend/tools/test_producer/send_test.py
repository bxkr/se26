from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
import psycopg2
from botocore.exceptions import ClientError
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError


RAW_BUCKET = os.getenv("RAW_BUCKET", "weather-raw")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "weather.actual.raw.created")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "weather")
POSTGRES_USER = os.getenv("POSTGRES_USER", "weather")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "weather")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
TEST_SOURCE_NAME = os.getenv("TEST_SOURCE_NAME", "historical_fetcher")
TEST_SCHEMA_VERSION = int(os.getenv("TEST_SCHEMA_VERSION", "1"))
EXPECTED_ROW_COUNT = int(os.getenv("EXPECTED_ROW_COUNT", "6"))


TEST_RAW_OBJECTS: dict[str, dict[str, Any]] = {
    "actual/date=1960-01-01.json": {
        "date": "1960-01-01",
        "stations": [
            {
                "wmo_index": "20674",
                "name": "Диксон",
                "country": "Россия",
                "min_temp": -35.1,
                "avg_temp": -31.9,
                "max_temp": -25.9,
                "precipitation": 0,
            },
            {
                "wmo_index": "20891",
                "name": "Хатанга",
                "country": "Россия",
                "min_temp": -29.0,
                "avg_temp": -27.5,
                "max_temp": -24.6,
                "precipitation": 0,
            },
        ],
    },
    "actual/date=1960-01-02.json": {
        "date": "1960-01-02",
        "stations": [
            {
                "wmo_index": "20674",
                "name": "Диксон",
                "country": "Россия",
                "min_temp": -34.2,
                "avg_temp": -30.8,
                "max_temp": -26.4,
                "precipitation": 0,
            },
            {
                "wmo_index": "20891",
                "name": "Хатанга",
                "country": "Россия",
                "min_temp": -28.4,
                "avg_temp": -26.9,
                "max_temp": -23.8,
                "precipitation": 0,
            },
        ],
    },
    "actual/date=1960-01-03.json": {
        "date": "1960-01-03",
        "stations": [
            {
                "wmo_index": "20674",
                "name": "Диксон",
                "country": "Россия",
                "min_temp": -33.7,
                "avg_temp": -30.1,
                "max_temp": -25.5,
                "precipitation": 0,
            },
            {
                "wmo_index": "20891",
                "name": "Хатанга",
                "country": "Россия",
                "min_temp": -27.8,
                "avg_temp": -26.0,
                "max_temp": -23.1,
                "precipitation": 0,
            },
        ],
    },
}


def log(message: str, **kwargs: Any) -> None:
    if kwargs:
        details = " ".join(f"{key}={value}" for key, value in kwargs.items())
        print(f"{message} | {details}", flush=True)
    else:
        print(message, flush=True)


def build_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
    )


def wait_for_s3(timeout_seconds: int = 60):
    s3 = build_s3_client()
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            s3.list_buckets()
            log("s3 is ready", endpoint=S3_ENDPOINT_URL)
            return s3
        except Exception as exc:
            log("waiting for s3", error=str(exc))
            time.sleep(2)

    raise TimeoutError("timed out waiting for s3")


def ensure_bucket(s3) -> None:
    try:
        s3.head_bucket(Bucket=RAW_BUCKET)
        log("bucket already exists", bucket=RAW_BUCKET)
        return
    except ClientError:
        pass

    s3.create_bucket(Bucket=RAW_BUCKET)
    log("bucket created", bucket=RAW_BUCKET)


def upload_raw_objects(s3) -> list[str]:
    object_keys = sorted(TEST_RAW_OBJECTS.keys())

    for object_key in object_keys:
        payload = TEST_RAW_OBJECTS[object_key]
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        s3.put_object(
            Bucket=RAW_BUCKET,
            Key=object_key,
            Body=body,
            ContentType="application/json; charset=utf-8",
        )

        log("uploaded raw object", bucket=RAW_BUCKET, object_key=object_key)

    return object_keys


def wait_for_kafka_admin(timeout_seconds: int = 60) -> KafkaAdminClient:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                client_id="test-producer-admin",
            )
            admin.list_topics()
            log("kafka admin is ready", bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
            return admin
        except Exception as exc:
            log("waiting for kafka admin", error=str(exc))
            time.sleep(2)

    raise TimeoutError("timed out waiting for kafka admin")


def ensure_topic() -> None:
    admin = wait_for_kafka_admin()
    try:
        topics = set(admin.list_topics())
        if KAFKA_TOPIC in topics:
            log("topic already exists", topic=KAFKA_TOPIC)
            return

        admin.create_topics(
            new_topics=[
                NewTopic(
                    name=KAFKA_TOPIC,
                    num_partitions=3,
                    replication_factor=1,
                )
            ],
            validate_only=False,
        )
        log("topic created", topic=KAFKA_TOPIC)
    except TopicAlreadyExistsError:
        log("topic already exists", topic=KAFKA_TOPIC)
    finally:
        admin.close()


def wait_for_kafka_producer(timeout_seconds: int = 60) -> KafkaProducer:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
                retries=5,
            )
            producer.bootstrap_connected()
            log("kafka producer is ready", bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
            return producer
        except Exception as exc:
            log("waiting for kafka producer", error=str(exc))
            time.sleep(2)

    raise TimeoutError("timed out waiting for kafka producer")


def build_event(object_keys: list[str]) -> dict[str, Any]:
    dates = [key.replace("actual/date=", "").replace(".json", "") for key in object_keys]

    return {
        "event_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "event_type": "weather.actual.raw.created",
        "source_name": TEST_SOURCE_NAME,
        "bucket": RAW_BUCKET,
        "object_keys": object_keys,
        "date_from": min(dates),
        "date_to": max(dates),
        "schema_version": TEST_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def send_event(event: dict[str, Any]) -> None:
    producer = wait_for_kafka_producer()
    try:
        future = producer.send(KAFKA_TOPIC, value=event)
        metadata = future.get(timeout=30)
        producer.flush()

        log(
            "event sent to kafka",
            topic=metadata.topic,
            partition=metadata.partition,
            offset=metadata.offset,
            event_id=event["event_id"],
            trace_id=event["trace_id"],
        )
    finally:
        producer.close()


def wait_for_postgres(timeout_seconds: int = 60):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            connection = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
            )
            connection.autocommit = True
            log("postgres is ready", host=POSTGRES_HOST, db=POSTGRES_DB)
            return connection
        except Exception as exc:
            log("waiting for postgres", error=str(exc))
            time.sleep(2)

    raise TimeoutError("timed out waiting for postgres")


def wait_for_etl_result(event_id: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        connection = None
        try:
            connection = wait_for_postgres(timeout_seconds=10)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM weather_actual
                    WHERE event_id = %s
                    """,
                    (event_id,),
                )
                row_count = cursor.fetchone()[0]

            log("polling etl result", event_id=event_id, row_count=row_count)

            if row_count == EXPECTED_ROW_COUNT:
                log("etl verification passed", event_id=event_id, row_count=row_count)
                return
        finally:
            if connection is not None:
                connection.close()

        time.sleep(3)

    raise TimeoutError(
        f"etl did not write expected rows in time; expected={EXPECTED_ROW_COUNT}, event_id={event_id}"
    )


def main() -> None:
    log("test producer started")

    s3 = wait_for_s3()
    ensure_bucket(s3)
    object_keys = upload_raw_objects(s3)

    ensure_topic()

    event = build_event(object_keys)
    log("prepared event", event=json.dumps(event, ensure_ascii=False))

    send_event(event)
    wait_for_etl_result(event["event_id"])

    log("e2e test completed successfully")


if __name__ == "__main__":
    main()