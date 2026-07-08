#!/usr/bin/env bash
set -euo pipefail

# `airflow standalone` creates its own admin user with a RANDOM password on
# first boot and ignores _AIRFLOW_WWW_USER_USERNAME/_AIRFLOW_WWW_USER_PASSWORD
# (those only apply to the docker-compose quick-start's separate `airflow
# users create` init step, not to the `standalone` subcommand). dm_trigger
# authenticates against the REST API with a known password, so we force it
# here once the user table exists.

WWW_USER="${_AIRFLOW_WWW_USER_USERNAME:-admin}"
WWW_PASSWORD="${_AIRFLOW_WWW_USER_PASSWORD:-admin}"

airflow standalone &
STANDALONE_PID=$!

echo "[entrypoint] waiting for airflow metadata DB to be ready..."
for _ in $(seq 1 60); do
  if airflow db check >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "[entrypoint] waiting for standalone to create its default admin user..."
for _ in $(seq 1 60); do
  if airflow users list 2>/dev/null | grep -q "^1 "; then
    break
  fi
  sleep 2
done

echo "[entrypoint] forcing known password for user '${WWW_USER}'..."
airflow users delete -u "${WWW_USER}" >/dev/null 2>&1 || true
airflow users create \
  -u "${WWW_USER}" \
  -p "${WWW_PASSWORD}" \
  -f Admin -l User -r Admin \
  -e "${WWW_USER}@example.com" \
  >/dev/null 2>&1 || true
echo "[entrypoint] admin credentials ready."

wait "${STANDALONE_PID}"
