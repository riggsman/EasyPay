from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "EasyPay"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "mysql+pymysql://easypay:easypay@localhost:3306/easypay"
    CORS_ORIGINS: str = "http://localhost:5173"
    DEFAULT_CURRENCY: str = "XAF"
    ALGORITHM: str = "HS256"

    NOTIFICATIONS_EMAIL_ENABLED: bool = True
    NOTIFICATIONS_SMS_ENABLED: bool = False
    NOTIFICATIONS_WHATSAPP_ENABLED: bool = True
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_USE_TLS: bool = True
    SMS_API_URL: str | None = None
    SMS_API_KEY: str | None = None
    WHATSAPP_API_URL: str | None = None
    WHATSAPP_API_KEY: str | None = None

    SOCKETIO_ENABLED: bool = True
    SOCKETIO_PATH: str = "/socket.io"
    SOCKETIO_REDIS_URL: str | None = None

    CONFIG_ENCRYPTION_KEY: str | None = None
    CAMPAY_BASE_URL: str = "https://demo.campay.net/api"
    CAMPAY_MOCK: bool = True

    # Public frontend base URL used in PDF QR deep-links (no trailing slash).
    # Change this when migrating to production, e.g. https://pay.example.com
    PUBLIC_BASE_URL: str = "http://localhost:5173"
    # Directory for tenant/platform logo files (relative to backend/ unless absolute)
    LOGO_STORAGE_DIR: str = "var/logos"
    # Logo watermark wash: 0.6 = 60% opacity (washed background mark)
    PDF_LOGO_WASH_OPACITY: float = 0.6

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def socketio_cors_origins(self) -> List[str]:
        return self.cors_origin_list if self.cors_origin_list else ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
