"""Storage backend factory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .local import LocalFileStorage
from .protocol import FileStorage
from .s3 import S3FileStorage

if TYPE_CHECKING:
    from app.config import Settings, StorageBackend
else:
    # Lazy import to avoid circular dependencies and import path issues
    Settings = None
    StorageBackend = None


def create_storage() -> FileStorage:
    """Factory function to create the appropriate storage backend.

    Returns:
        FileStorage instance based on configuration.

    Raises:
        ValueError: If S3 backend is selected but bucket name is missing.
    """
    # Import here to avoid import path issues
    from app.config import StorageBackend, settings

    if settings.storage_backend == StorageBackend.S3:
        if not settings.s3_bucket_name:
            raise ValueError("S3 bucket name is required when using S3 storage backend")

        return S3FileStorage(
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
            aws_profile=settings.aws_profile,
        )

    data_dir = Path(settings.local_data_dir).resolve()
    return LocalFileStorage(data_dir)
