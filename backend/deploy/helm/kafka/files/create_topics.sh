#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-kafka:9092}"

# Для текущего historical flow обязателен weather.actual.raw.created.
# Остальные темы оставляем как совместимые с текущими contracts.
TOPICS=(
  "weather.actual.raw.created:3:1:604800000"
  "weather.forecast.raw.created:3:1:604800000"
  "weather.clean.created:3:1:604800000"
  "weather.need_info:3:1:604800000"
  "weather.dm.ready:3:1:604800000"
  "weather.pipeline.failed:3:1:604800000"
)

echo "Waiting for Kafka at ${BOOTSTRAP_SERVER}..."
until kafka-topics --bootstrap-server "${BOOTSTRAP_SERVER}" --list >/dev/null 2>&1; do
  sleep 2
done

echo "Kafka is available. Creating topics..."

for spec in "${TOPICS[@]}"; do
  IFS=":" read -r topic partitions replication retention_ms <<< "${spec}"

  kafka-topics \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions "${partitions}" \
    --replication-factor "${replication}" \
    --config retention.ms="${retention_ms}"

  echo "Ensured topic exists: ${topic}"
done

echo
echo "Kafka topics description:"
for spec in "${TOPICS[@]}"; do
  IFS=":" read -r topic partitions replication retention_ms <<< "${spec}"
  kafka-topics \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --describe \
    --topic "${topic}"
done

echo
echo "Kafka topics are ready."