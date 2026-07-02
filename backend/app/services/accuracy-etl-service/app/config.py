from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSTGRES_PORT: int
    REDIS_PORT: int
    S3_PORT: int
    MINIO_CONSOLE_PORT: int
    KAFKA_UI_PORT: int
    KAFKA_EXTERNAL_PORT: int
    CLICKHOUSE_PORT: int
    CLICKHOUSE_NATIVE_PORT: int
    FORECAST_SERVICE_PORT: int
    ACTUAL_SERVICE_PORT: int
    ANALYTICS_API_SERVICE_PORT: int
    ALERT_SERVICE_PORT: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()