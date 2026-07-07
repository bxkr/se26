#!/usr/bin/env bash
set -euo pipefail

MINIO_ALIAS="${MINIO_ALIAS:-local}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"

RAW_BUCKET="${RAW_BUCKET:-weather-raw}"

echo "Waiting for MinIO at ${MINIO_ENDPOINT}..."
until mc alias set "${MINIO_ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  sleep 2
done

echo "MinIO is available. Creating bucket ${RAW_BUCKET}..."
mc mb --ignore-existing "${MINIO_ALIAS}/${RAW_BUCKET}"

# Bucket remains private; ETL/fetchers use service credentials.
mc anonymous set private "${MINIO_ALIAS}/${RAW_BUCKET}" >/dev/null 2>&1 || true

echo "Bucket is ready: ${RAW_BUCKET}"
echo "Canonical historical raw object key format: actual/date=YYYY-MM-DD.json"