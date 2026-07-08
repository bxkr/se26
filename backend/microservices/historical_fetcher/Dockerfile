FROM eclipse-temurin:21-jdk AS build

WORKDIR /build


COPY gradle/ ./gradle
COPY gradlew ./

RUN sed -i 's/\r$//' gradlew && chmod +x gradlew && ./gradlew --version --no-daemon


COPY build.gradle settings.gradle ./


RUN ./gradlew dependencies --no-daemon || true


COPY src ./src


RUN ./gradlew clean bootJar -x test --no-daemon


FROM eclipse-temurin:21-jre

WORKDIR /app


COPY --from=build /build/build/libs/*.jar /app/app.jar


ENV JAVA_OPTS="-Xms512m -Xmx512m"

EXPOSE 5050

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]