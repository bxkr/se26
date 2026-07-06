#!/bin/sh
set -e

echo "Creating Kafka topics..."

kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic need_info --partitions 1 --replication-factor 1
kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic new_raw_historical --partitions 2 --replication-factor 1
kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic new_raw_predict --partitions 2 --replication-factor 1
kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic new_clean --partitions 1 --replication-factor 1

echo "Kafka topics created"
kafka-topics --bootstrap-server kafka:29092 --list