from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PRISM"
    app_env: str = "development"
    app_debug: bool = False
    log_level: str = "INFO"
    max_upload_size_mb: int = 50
    default_currency: str = "EUR"
    enable_sample_data: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
