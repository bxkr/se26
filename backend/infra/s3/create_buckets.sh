#!/bin/sh
set -e

sleep 5
mc alias set local http://minio:9000 minioadmin minioadmin
mc mb -p local/weather-raw || true
echo "S3 buckets created"