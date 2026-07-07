FROM apache/airflow:2.9.3-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="/home/airflow/.local/bin:${JAVA_HOME}/bin:${PATH}"

# JDBC drivers used by spark_jobs/postgres_to_clickhouse.py (via --jars in
# the DAG's spark-submit command, not auto-discovered).
RUN mkdir -p /opt/spark_jars \
    && curl -fsSL -o /opt/spark_jars/postgresql.jar \
        https://jdbc.postgresql.org/download/postgresql-42.7.3.jar \
    && curl -fsSL -o /opt/spark_jars/clickhouse-jdbc.jar \
        https://repo1.maven.org/maven2/com/clickhouse/clickhouse-jdbc/0.6.3/clickhouse-jdbc-0.6.3-all.jar

COPY spark_jobs /opt/spark_jobs
RUN mkdir -p /opt/airflow/spark_results && chown -R airflow:root /opt/airflow/spark_results

USER airflow

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY dags /opt/airflow/dags
COPY common /opt/airflow/dags/common
COPY --chmod=755 docker-entrypoint.sh /opt/airflow/docker-entrypoint.sh

ENV AIRFLOW__CORE__LOAD_EXAMPLES=false
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor

ENTRYPOINT ["/opt/airflow/docker-entrypoint.sh"]
