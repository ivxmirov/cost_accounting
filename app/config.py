from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    databases_dsn: str = ""
    redis_dsn: str = ""
    redis_cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
