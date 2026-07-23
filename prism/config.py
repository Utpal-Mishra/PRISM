from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from prism.version import __version__


class Settings(BaseSettings):
    app_name: str = "PRISM"
    app_version: str = __version__
    app_env: str = "development"
    app_debug: bool = False
    log_level: str = "INFO"
    log_directory: str = "logs"
    max_upload_size_mb: int = 50
    default_currency: str = "EUR"
    enable_sample_data: bool = True
    enable_demo_mode: bool = True
    enable_authentication: bool = False
    app_access_code: SecretStr = SecretStr("")
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
