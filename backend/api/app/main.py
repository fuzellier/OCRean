"""Minimal FastAPI application with upload/OCR support."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from .services.files import FileStorage
from .services.ocr import OCRProcessor
from .services.text import TextProcessor

app = FastAPI(title="OCRean API", version="0.1.0")

# Initialize storage service (local data directory)
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
file_storage = FileStorage(DATA_DIR)
ocr_processor = OCRProcessor(use_gpu=True)
text_processor = TextProcessor()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello, World!"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/documents/upload")
async def upload_document(file: Annotated[UploadFile, File()]):
    """Upload an image or PDF and receive a document ID."""
    document_id = await file_storage.save_uploaded_file(file)
    return {"document_id": document_id}


@app.post("/documents/{document_id}/ocr")
async def run_ocr(document_id: str):
    """Run OCR against a previously uploaded document."""
    document_path = file_storage.get_raw_file_path(document_id)
    if not document_path:
        raise HTTPException(status_code=404, detail="Document not found. Upload first.")

    text = ocr_processor.extract_text(document_path)
    file_storage.save_ocr_text(document_id, text)
    return {"document_id": document_id, "text": text}


@app.post("/documents/{document_id}/sentences")
async def generate_sentences(document_id: str):
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
async def extract_vocabulary(document_id: str, min_length: int = 1):
    """Extract Korean vocabulary from OCR text."""
    text = file_storage.load_ocr_text(document_id)
    vocabulary = text_processor.extract_vocabulary(text, min_length=min_length)
    return {
        "document_id": document_id,
        "vocabulary": vocabulary,
        "vocabulary_count": len(vocabulary),
        "min_length": min_length,
    }
