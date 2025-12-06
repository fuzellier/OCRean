"""Local file storage helpers for uploads, OCR output, and processed text."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

PDF_CONTENT_TYPE = "application/pdf"
IMAGE_PREFIX = "image/"
DEFAULT_IMAGE_EXTENSION = ".jpg"


@dataclass(slots=True)
class StoragePaths:
    """Resolved directories for raw uploads, OCR output, and processed text."""

    base_dir: Path
    raw: Path = field(init=False)
    ocr: Path = field(init=False)
    sentences: Path = field(init=False)

    def __post_init__(self) -> None:
        self.raw = self.base_dir / "raw"
        self.ocr = self.base_dir / "ocr"
        self.sentences = self.base_dir / "sentences"

    def ensure_exists(self) -> None:
        """Create required directories if they don't exist."""
        for path in (self.raw, self.ocr, self.sentences):
            path.mkdir(parents=True, exist_ok=True)


class LocalFileStorage:
    """Local file storage manager for uploaded documents and derived data."""

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
        document_id = self._validate_document_id(document_id)
        matches = list(self.paths.raw.glob(f"{document_id}.*"))
        return matches[0] if matches else None

    def get_raw_file_content(self, document_id: str) -> bytes:
        """Get raw file content as bytes for processing."""
        file_path = self.get_raw_file_path(document_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="Document not found")
        return file_path.read_bytes()

    def load_ocr_text(self, document_id: str) -> str:
        """Load OCR output text or raise if it doesn't exist."""
        document_id = self._validate_document_id(document_id)
        ocr_path = self.paths.ocr / f"{document_id}.txt"
        if not ocr_path.exists():
            raise HTTPException(
                status_code=404,
                detail="OCR text not found. Run /documents/{id}/ocr first.",
            )
        return ocr_path.read_text(encoding="utf-8")

    def save_ocr_text(self, document_id: str, text: str) -> Path:
        """Persist OCR output for future reuse."""
        document_id = self._validate_document_id(document_id)
        ocr_path = self.paths.ocr / f"{document_id}.txt"
        ocr_path.write_text(text, encoding="utf-8")
        return ocr_path

    def save_sentences(self, document_id: str, data: Mapping[str, Any]) -> Path:
        """Store processed sentence data for later inspection."""
        document_id = self._validate_document_id(document_id)
        path = self.paths.sentences / f"{document_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_sentences(self, document_id: str) -> dict[str, Any]:
        """Load stored sentence data if available."""
        document_id = self._validate_document_id(document_id)
        path = self.paths.sentences / f"{document_id}.json"
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail="No sentence data found. Run /documents/{id}/sentences first.",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def _validate_document_id(self, document_id: str) -> str:
        """Ensure the supplied document ID is a canonical UUID string."""
        try:
            validated = uuid.UUID(str(document_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid document_id format.") from exc
        return str(validated)

    def _resolve_extension(self, file: UploadFile, content_type: str) -> str:
        """Determine the file extension for an upload based on its metadata."""
        if content_type == PDF_CONTENT_TYPE:
            return ".pdf"

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
