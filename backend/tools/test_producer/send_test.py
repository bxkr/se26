from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable, TopicAlreadyExistsError


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
REQUEST_TOPIC = os.getenv("REQUEST_TOPIC", "weather.need_info")
RAW_CREATED_TOPIC = os.getenv("RAW_CREATED_TOPIC", "weather.actual.raw.created")

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
RAW_BUCKET = os.getenv("RAW_BUCKET", "weather-raw")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "weather")
POSTGRES_USER = os.getenv("POSTGRES_USER", "weather")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "weather")

REQUEST_SOURCE_NAME = os.getenv("REQUEST_SOURCE_NAME", "test_producer")
EXPECTED_RAW_SOURCE_NAME = os.getenv("EXPECTED_RAW_SOURCE_NAME", "historical_fetcher")
TEST_SCHEMA_VERSION = int(os.getenv("TEST_SCHEMA_VERSION", "1"))
EXPECTED_ROW_COUNT = int(os.getenv("EXPECTED_ROW_COUNT", "6"))
EXPECTED_OBJECT_KEYS_COUNT = int(os.getenv("EXPECTED_OBJECT_KEYS_COUNT", "3"))

REQUEST_DATE_FROM = os.getenv("REQUEST_DATE_FROM", "1960-01-01")
REQUEST_DATE_TO = os.getenv("REQUEST_DATE_TO", "1960-01-03")

WAIT_TIMEOUT_SECONDS = int(os.getenv("WAIT_TIMEOUT_SECONDS", "300"))
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "3"))

# Если твой InputEvent.java ожидает другой shape, проще всего поменять только:
# - build_need_info_event()
# - REQUEST_STATIONS_JSON / NEED_INFO_PAYLOAD_JSON
DEFAULT_STATIONS = ["20674","20891"]


def log(message: str, **kwargs: Any) -> None:
    if kwargs:
        details = " ".join(f"{key}={value}" for key, value in kwargs.items())
        print(f"{message} | {details}", flush=True)
    else:
        print(message, flush=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_request_stations() -> list[str]:
    raw = os.getenv("REQUEST_STATIONS_JSON")
    if not raw:
        
        return DEFAULT_STATIONS
    return DEFAULT_STATIONS


def build_need_info_event() -> dict[str, Any]:
    override_raw = os.getenv("NEED_INFO_PAYLOAD_JSON")

    event_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    created_at = utc_now_iso()

    if override_raw:
        payload = json.loads(override_raw)
    else:
        payload = {
            "event_id": event_id,
            "trace_id": trace_id,
            "event_type": "weather.need_info",
            "requested_by": REQUEST_SOURCE_NAME,
            "date_from": REQUEST_DATE_FROM,
            "date_to": REQUEST_DATE_TO,
            "wmo_indexes": load_request_stations(),
            "schema_version": TEST_SCHEMA_VERSION,
            "created_at": created_at,
            "dataset_type": "weather-raw"
        }

    payload.setdefault("event_id", event_id)
    payload.setdefault("trace_id", trace_id)
    payload.setdefault("event_type", "weather.need_info")
    payload.setdefault("requested_by", REQUEST_SOURCE_NAME)
    payload.setdefault("schema_version", TEST_SCHEMA_VERSION)
    payload.setdefault("created_at", created_at)

    return payload


def build_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
    )


def wait_for_s3(timeout_seconds: int = 60):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            s3 = build_s3_client()
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


def ensure_topics() -> None:
    admin = wait_for_kafka_admin()
    try:
        existing = set(admin.list_topics())
        specs = [
            (REQUEST_TOPIC, 3),
            (RAW_CREATED_TOPIC, 3),
        ]

        to_create = []
        for topic_name, partitions in specs:
            if topic_name in existing:
                log("topic already exists", topic=topic_name)
                continue
            to_create.append(
                NewTopic(
                    name=topic_name,
                    num_partitions=partitions,
                    replication_factor=1,
                )
            )

        if to_create:
            admin.create_topics(new_topics=to_create, validate_only=False)
            for topic in to_create:
                log("topic created", topic=topic.name)
    except TopicAlreadyExistsError:
        log("topic already exists due to race condition")
    finally:
        admin.close()


def wait_for_kafka_producer(timeout_seconds: int = 60) -> KafkaProducer:
    deadline = time.time() + timeout_seconds
    last_error: str | None = None

    while time.time() < deadline:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
                retries=5,
            )
            if producer.bootstrap_connected():
                log("kafka producer is ready", bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
                return producer

            producer.close()
            last_error = "bootstrap not connected yet"
        except NoBrokersAvailable as exc:
            last_error = str(exc)
        except Exception as exc:
            last_error = str(exc)

        log("waiting for kafka producer", error=last_error)
        time.sleep(2)

    raise TimeoutError(f"timed out waiting for kafka producer: {last_error}")


def build_raw_created_consumer(timeout_seconds: int = 60) -> KafkaConsumer:
    consumer = KafkaConsumer(
        RAW_CREATED_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"test-producer-raw-wait-{uuid.uuid4()}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        consumer_timeout_ms=1000,
    )

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        consumer.poll(timeout_ms=1000)
        if consumer.assignment():
            log(
                "raw.created consumer is ready",
                topic=RAW_CREATED_TOPIC,
                assigned_partitions=len(consumer.assignment()),
            )
            return consumer

    consumer.close()
    raise TimeoutError("timed out waiting for raw.created consumer assignment")


def send_need_info_event(event: dict[str, Any]) -> None:
    producer = wait_for_kafka_producer()
    try:
        future = producer.send(REQUEST_TOPIC, value=event)
        metadata = future.get(timeout=30)
        producer.flush()

        log(
            "need_info event sent to kafka",
            topic=metadata.topic,
            partition=metadata.partition,
            offset=metadata.offset,
            event_id=event.get("event_id"),
            trace_id=event.get("trace_id"),
        )
    finally:
        producer.close()


def wait_for_raw_created_event(
    *, consumer: KafkaConsumer, request_event: dict[str, Any], timeout_seconds: int
) -> dict[str, Any]:
    """Poll RAW_CREATED_TOPIC until historical_fetcher's receipt for our
    trace_id shows up, or time out. historical_fetcher passes trace_id
    through from InputEvent to OutputReceipt unchanged, so it's the
    correlation key between what we sent and what we get back."""
    expected_trace_id = request_event["trace_id"]
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        for message in consumer.poll(timeout_ms=1000).values():
            for record in message:
                event = record.value
                if event.get("trace_id") == expected_trace_id:
                    log(
                        "matching raw.created event received",
                        event_id=event.get("event_id"),
                        trace_id=event.get("trace_id"),
                        object_keys=event.get("object_keys"),
                    )
                    return event

    raise TimeoutError(
        f"timed out waiting for {RAW_CREATED_TOPIC} with trace_id={expected_trace_id} "
        f"(historical_fetcher didn't respond in {timeout_seconds}s)"
    )


def verify_raw_created_event(event: dict[str, Any]) -> None:
    errors = []

    if event.get("event_type") != "weather.actual.raw.created":
        errors.append(f"event_type={event.get('event_type')!r}, expected weather.actual.raw.created")
    if event.get("source_name") != EXPECTED_RAW_SOURCE_NAME:
        errors.append(f"source_name={event.get('source_name')!r}, expected {EXPECTED_RAW_SOURCE_NAME!r}")
    if event.get("bucket") != RAW_BUCKET:
        errors.append(f"bucket={event.get('bucket')!r}, expected {RAW_BUCKET!r}")

    object_keys = event.get("object_keys") or []
    if len(object_keys) != EXPECTED_OBJECT_KEYS_COUNT:
        errors.append(
            f"object_keys count={len(object_keys)}, expected {EXPECTED_OBJECT_KEYS_COUNT} "
            f"(date range {REQUEST_DATE_FROM}..{REQUEST_DATE_TO}): {object_keys}"
        )

    if errors:
        raise AssertionError("raw.created event failed verification: " + "; ".join(errors))

    log("raw.created event shape verified", object_keys=object_keys)


def verify_s3_objects(s3, object_keys: list[str], requested_stations: list[str]) -> None:
    """Fetch every object historical_fetcher claims to have written and check
    it actually exists in S3, is valid JSON, and only contains the stations
    we asked for (the API returns many more stations than we requested;
    EventProcessor filters down to targetWmoIndexes)."""
    total_rows = 0

    for object_key in object_keys:
        body = s3.get_object(Bucket=RAW_BUCKET, Key=object_key)["Body"].read()
        payload = json.loads(body)

        stations = payload.get("stations") or []
        found_wmo_indexes = {str(station.get("wmo_index")) for station in stations}
        unexpected = found_wmo_indexes - set(requested_stations)
        if unexpected:
            raise AssertionError(f"{object_key}: unexpected stations not in request: {unexpected}")

        total_rows += len(stations)
        log("verified s3 object", object_key=object_key, station_count=len(stations))

    if total_rows != EXPECTED_ROW_COUNT:
        raise AssertionError(
            f"total station rows across {len(object_keys)} object(s) = {total_rows}, "
            f"expected {EXPECTED_ROW_COUNT}"
        )

    log("s3 objects verified", total_rows=total_rows)


def main() -> None:
    log("historical_fetcher infrastructure test started")

    s3 = wait_for_s3()
    ensure_bucket(s3)
    ensure_topics()

    raw_consumer = build_raw_created_consumer()

    request_event = build_need_info_event()
    log("prepared need_info event", event=json.dumps(request_event, ensure_ascii=False))

    send_need_info_event(request_event)

    try:
        raw_event = wait_for_raw_created_event(
            consumer=raw_consumer,
            request_event=request_event,
            timeout_seconds=WAIT_TIMEOUT_SECONDS,
        )
    finally:
        raw_consumer.close()

    verify_raw_created_event(raw_event)
    verify_s3_objects(s3, raw_event["object_keys"], request_event["wmo_indexes"])

    log("historical_fetcher infrastructure test PASSED")


if __name__ == "__main__":
    main()