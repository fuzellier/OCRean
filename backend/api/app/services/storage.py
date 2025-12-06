"""Storage backend abstraction and factory."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile


class FileStorage(Protocol):
    """Protocol defining the storage interface for document management.

    This protocol ensures all storage backends implement the same interface,
    making them interchangeable.
    """

    async def save_uploaded_file(self, file: UploadFile) -> str:
        """Persist an uploaded PDF/image and return its document ID."""
        ...

    def get_raw_file_path(self, document_id: str) -> Path | str | None:
        """Return the stored raw file path/key if it exists."""
        ...

    def get_raw_file_content(self, document_id: str) -> bytes:
        """Get raw file content as bytes for processing."""
        ...

    def load_ocr_text(self, document_id: str) -> str:
        """Load OCR output text or raise if it doesn't exist."""
        ...

    def save_ocr_text(self, document_id: str, text: str) -> Path | str:
        """Persist OCR output for future reuse."""
        ...

    def save_sentences(self, document_id: str, data: Mapping[str, Any]) -> Path | str:
        """Store processed sentence data for later inspection."""
        ...

    def load_sentences(self, document_id: str) -> dict[str, Any]:
        """Load stored sentence data if available."""
        ...


def create_storage() -> FileStorage:
    """Factory function to create the appropriate storage backend.

    Returns:
        FileStorage instance based on configuration.

    Raises:
        ValueError: If S3 backend is selected but bucket name is missing.
    """
    from pathlib import Path

    from ..config import StorageBackend, settings
    from .files import LocalFileStorage
    from .s3_storage import S3FileStorage

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
