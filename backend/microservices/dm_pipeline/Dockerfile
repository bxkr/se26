FROM apache/airflow:2.9.3-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="/home/airflow/.local/bin:${JAVA_HOME}/bin:${PATH}"

# JARs used by spark_jobs/s3_to_clickhouse.py (via --jars in the DAG's
# spark-submit command, not auto-discovered): hadoop-aws + aws-java-sdk-bundle
# give Spark the S3A filesystem connector to read raw JSON straight from S3;
# clickhouse-jdbc is still needed to write the RAW/ODS/DM layers out.
# Versions matched to pyspark==3.5.1's bundled Hadoop 3.3.4.
RUN mkdir -p /opt/spark_jars \
    && curl -fsSL -o /opt/spark_jars/hadoop-aws.jar \
        https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
    && curl -fsSL -o /opt/spark_jars/aws-java-sdk-bundle.jar \
        https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar \
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
