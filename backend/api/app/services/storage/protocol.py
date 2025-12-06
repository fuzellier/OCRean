"""Storage backend protocol definition."""

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
