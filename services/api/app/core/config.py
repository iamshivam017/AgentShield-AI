from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    app_name: str = "AgentShield API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./agentshield.db"
    jwt_secret: str
    demo_user_password: str | None = None
    access_token_ttl_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    llm_provider: Literal["deterministic", "openai"] = "deterministic"
    openai_api_key: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    razorpay_test_mode: bool = True
    rate_limit_per_minute: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def validate_runtime(self) -> None:
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if not self.razorpay_test_mode:
            raise ValueError("AgentShield buildathon release only supports Razorpay test mode")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
