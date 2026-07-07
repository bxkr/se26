# Stage 1: build with Gradle wrapper on JDK 21
FROM eclipse-temurin:21-jdk-jammy AS builder

WORKDIR /home/app

# Нужны bash/unzip для gradle wrapper
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy gradle wrapper and project files
COPY build.gradle settings.gradle gradlew gradlew.bat /home/app/
COPY gradle /home/app/gradle
COPY src /home/app/src

# Ensure wrapper is executable
RUN chmod +x gradlew

# Build jar
RUN ./gradlew --no-daemon clean build

# Найти runnable jar и скопировать в фиксированное имя
RUN JAR_PATH=$(find /home/app/build/libs -type f -name "*.jar" ! -name "*-plain.jar" | head -n 1) \
    && test -n "$JAR_PATH" \
    && cp "$JAR_PATH" /home/app/app.jar

# Stage 2: runtime on JRE 21
FROM eclipse-temurin:21-jre-jammy

WORKDIR /app

COPY --from=builder /home/app/app.jar /app/app.jar

ENV JAVA_OPTS=""
ENV KAFKA_BOOTSTRAP_SERVERS="kafka:9092"
ENV S3_ENDPOINT="http://minio:9000"
ENV S3_ACCESS_KEY="minioadmin"
ENV S3_SECRET_KEY="minioadmin"
ENV RAW_BUCKET="weather-raw"

EXPOSE 8080

CMD ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]