from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./pipeline.db"
    apify_token: str = ""
    apify_actor_id: str = "aimscrape~instagram-scraper"
    destination_url: str = ""
    max_results_per_query: int = 5
    apify_timeout_secs: int = 300
    dedupe_enabled: bool = True
    destination_retries: int = 3
    destination_retry_backoff_sec: float = 1.0
    pipeline_fail_closed: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Stored on Run for UI; must fit valid JSON — 12k was too small for several reels with long CDN URLs.
    payload_preview_max_chars: int = Field(default=1_000_000, ge=1000, le=5_000_000)

    redis_url: str = ""
    rq_queue_name: str = "pipeline"

    media_storage: Literal["none", "local", "s3"] = "none"
    media_local_root: str = "./media"
    # Used in payload video_url when MEDIA_STORAGE=local (short link served by GET /media/...)
    media_public_base_url: str = "http://127.0.0.1:8000"
    max_bytes_per_video: int = 100 * 1024 * 1024
    download_timeout_sec: float = 120.0
    max_concurrent_downloads: int = 1

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_prefix: str = ""

    @field_validator("media_storage", mode="before")
    @classmethod
    def lower_storage(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator("media_storage")
    @classmethod
    def allowed_storage(cls, v: str) -> str:
        if v not in ("none", "local", "s3"):
            raise ValueError("media_storage must be none, local, or s3")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_rq(self) -> bool:
        return bool(self.redis_url.strip())


def get_settings() -> Settings:
    return Settings()
