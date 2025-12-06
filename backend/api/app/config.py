"""Application configuration using environment variables."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageBackend(str, Enum):
    """Supported storage backend types."""

    LOCAL = "local"
    S3 = "s3"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Look for .env in backend/ directory (parent of api/)
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Storage configuration
    storage_backend: StorageBackend = StorageBackend.LOCAL
    local_data_dir: str = "data"

    # S3 configuration (used when storage_backend is S3)
    s3_bucket_name: str = ""
    s3_region: str = "eu-west-3"

    # AWS CLI profile name
    aws_profile: str = ""

    # OCR configuration
    use_gpu: bool = True


# Global settings instance
settings = Settings()
