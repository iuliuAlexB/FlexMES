from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://flexmes:flexmes@db:5432/flexmes"
    SECRET_KEY: str = "flexmes-secret-key-minimum-32-chars-change-in-prod"
    CSRF_SECRET: str = "flexmes-csrf-secret-change-in-prod"
    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_TOPIC_PREFIX: str = "flexmes"
    DEBUG: bool = False


settings = Settings()
