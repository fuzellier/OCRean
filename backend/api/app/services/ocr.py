"""OCR service that turns images or PDFs into plain text."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import easyocr
import numpy as np
from fastapi import HTTPException
from PIL import Image

DEFAULT_LANGUAGES: Sequence[str] = ("ko", "en")
PDF_SUFFIX = ".pdf"


class OCRProcessor:
    """Coordinates EasyOCR for both images and PDFs."""

    def __init__(
        self,
        languages: Iterable[str] | None = None,
        use_gpu: bool | None = None,
        pdf_dpi: int = 200,
    ) -> None:
        self.languages = tuple(languages or DEFAULT_LANGUAGES)
        self.use_gpu = self._resolve_gpu_flag(use_gpu)
        self.pdf_dpi = pdf_dpi
        self._reader: easyocr.Reader | None = None

    def extract_text(self, document_path: Path) -> str:
        """Detect text inside an image or PDF file."""
        if not document_path.exists():
            raise HTTPException(status_code=404, detail="Document not found on disk.")

        if document_path.suffix.lower() == PDF_SUFFIX:
            pages = self._convert_pdf_to_images(document_path)
            if not pages:
                raise HTTPException(status_code=400, detail="No pages detected in PDF.")
            chunks = [self._run_ocr(page) for page in pages]
        else:
            chunks = [self._run_ocr(document_path)]

        text = "\n\n".join(chunk for chunk in chunks if chunk)
        return text.strip()

    # Internal helpers -----------------------------------------------------

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            self._reader = easyocr.Reader(self.languages, gpu=self.use_gpu)
        return self._reader

    def _run_ocr(self, source: Path | Image.Image) -> str:
        reader = self._get_reader()
        if isinstance(source, Path):
            results = reader.readtext(str(source))
        else:
            results = reader.readtext(np.array(source))
        return " ".join(item[1] for item in results)

    def _convert_pdf_to_images(self, pdf_path: Path) -> list[Image.Image]:
        try:
            from pdf2image import convert_from_path
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise HTTPException(
                status_code=500,
                detail="pdf2image is required for PDF OCR. Install poppler and pdf2image.",
            ) from exc

        try:
            return convert_from_path(str(pdf_path), dpi=self.pdf_dpi)
        except Exception as exc:  # pragma: no cover - conversion issues
            raise HTTPException(
                status_code=500, detail=f"Failed to convert PDF to images: {exc}"
            ) from exc

    @staticmethod
    def _resolve_gpu_flag(requested: bool | None) -> bool:
        if requested is not None:
            return requested

        try:
            import torch  # type: ignore

            return torch.cuda.is_available()
        except Exception:  # pragma: no cover - torch optional
            return False
