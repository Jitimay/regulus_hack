"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google Cloud
    google_cloud_project: str = Field(default="regulus-demo")
    google_cloud_region: str = Field(default="us-central1")
    google_application_credentials: str = Field(default="")

    # Gemini
    gemini_model: str = Field(default="gemini-3.6-flash")

    # Firestore
    firestore_database: str = Field(default="(default)")

    # Pub/Sub
    pubsub_topic: str = Field(default="regulus-runs")
    pubsub_subscription: str = Field(default="regulus-runs-sub")

    # CORS
    allowed_origin: str = Field(default="http://localhost:3000")

    # App
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    log_level: str = Field(default="INFO")
    simulation_count: int = Field(default=500)
    max_research_loops: int = Field(default=3)

    # Mock flags for local dev without GCP credentials
    use_mock_research: bool = Field(default=True)
    use_mock_firestore: bool = Field(default=False)
    use_mock_pubsub: bool = Field(default=False)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
