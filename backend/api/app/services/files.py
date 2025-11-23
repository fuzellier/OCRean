"""File storage helpers for uploads (local “mini-S3”)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, UploadFile

PDF_CONTENT_TYPE = "application/pdf"
IMAGE_PREFIX = "image/"
DEFAULT_IMAGE_EXTENSION = ".jpg"


@dataclass(slots=True)
class StoragePaths:
    """Resolved directories for raw uploads."""

    base_dir: Path
    raw: Path = field(init=False)
    ocr: Path = field(init=False)

    def __post_init__(self) -> None:
        self.raw = self.base_dir / "raw"
        self.ocr = self.base_dir / "ocr"

    def ensure_exists(self) -> None:
        """Create required directories if they don't exist."""
        for path in (self.raw, self.ocr):
            path.mkdir(parents=True, exist_ok=True)


class FileStorage:
    """Local file storage manager for uploaded documents."""

    def __init__(self, base_dir: Path):
        self.paths = StoragePaths(base_dir)
        self.paths.ensure_exists()

    async def save_uploaded_file(self, file: UploadFile) -> str:
        """Persist an uploaded PDF/image and return its document ID."""
        content_type = file.content_type
        if not content_type:
            raise HTTPException(status_code=400, detail="Could not determine file type")

        extension = self._resolve_extension(file, content_type)
        document_id = str(uuid.uuid4())
        file_path = self.paths.raw / f"{document_id}{extension}"

        try:
            file_path.write_bytes(await file.read())
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="Failed to save file") from exc

        return document_id

    def get_raw_file_path(self, document_id: str) -> Path | None:
        """Return the stored raw file path if it exists."""
        matches = list(self.paths.raw.glob(f"{document_id}.*"))
        return matches[0] if matches else None

    def save_ocr_text(self, document_id: str, text: str) -> Path:
        """Persist OCR output for future reuse."""
        ocr_path = self.paths.ocr / f"{document_id}.txt"
        ocr_path.write_text(text, encoding="utf-8")
        return ocr_path

    def _resolve_extension(self, file: UploadFile, content_type: str) -> str:
        """Determine the file extension for an upload based on its metadata."""
        if content_type == PDF_CONTENT_TYPE:
            return ".pdf"

        # For images, prefer whatever extension the client provided, fallback to JPG.
        if content_type.startswith(IMAGE_PREFIX):
            if file.filename:
                suffix = Path(file.filename).suffix
                if suffix:
                    return suffix
            return DEFAULT_IMAGE_EXTENSION

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Only images and PDFs are supported.",
        )
