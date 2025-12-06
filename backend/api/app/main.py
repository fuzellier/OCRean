"""FastAPI application exposing upload, OCR, and text-processing endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from .config import settings
from .services import OCRProcessor, TextProcessor, create_storage

app = FastAPI(title="OCRean API", version="0.1.0")

# Initialize services using factory pattern
file_storage = create_storage()
ocr_processor = OCRProcessor(use_gpu=settings.use_gpu)
text_processor = TextProcessor()


@app.get("/")
async def root() -> dict[str, str]:
    """Simple connectivity check."""
    return {"message": "Hello, World!"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe endpoint."""
    return {"status": "healthy"}


@app.post("/documents/upload")
async def upload_document(file: Annotated[UploadFile, File()]) -> dict[str, str]:
    """Upload an image or PDF and receive a document ID."""
    document_id = await file_storage.save_uploaded_file(file)
    return {"document_id": document_id}


@app.post("/documents/{document_id}/ocr")
async def run_ocr(document_id: str) -> dict[str, str]:
    """Run OCR against a previously uploaded document."""
    if not file_storage.get_raw_file_path(document_id):
        raise HTTPException(status_code=404, detail="Document not found. Upload first.")

    # Get file content and extension - storage backend handles the details
    file_content = file_storage.get_raw_file_content(document_id)
    document_path_or_key = file_storage.get_raw_file_path(document_id)

    # Determine file extension from path/key
    file_extension = Path(str(document_path_or_key)).suffix

    # Process with OCR
    text = ocr_processor.extract_text_from_bytes(file_content, file_extension)

    file_storage.save_ocr_text(document_id, text)
    return {"document_id": document_id, "text": text}


@app.post("/documents/{document_id}/sentences")
async def generate_sentences(document_id: str) -> dict[str, object]:
    """Split OCR text into sentences and persist the result."""
    text = file_storage.load_ocr_text(document_id)
    sentences = text_processor.split_into_sentences(text)
    payload = {
        "document_id": document_id,
        "sentences": sentences,
        "sentence_count": len(sentences),
    }
    file_storage.save_sentences(document_id, payload)
    return payload


@app.post("/documents/{document_id}/vocabulary")
async def extract_vocabulary(document_id: str, min_length: int = 1) -> dict[str, object]:
    """Extract Korean vocabulary from OCR text."""
    text = file_storage.load_ocr_text(document_id)
    vocabulary = text_processor.extract_vocabulary(text, min_length=min_length)
    return {
        "document_id": document_id,
        "vocabulary": vocabulary,
        "vocabulary_count": len(vocabulary),
        "min_length": min_length,
    }
