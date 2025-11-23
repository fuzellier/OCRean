"""Minimal FastAPI application with upload support."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, UploadFile

from .services.files import FileStorage

app = FastAPI(title="OCRean API", version="0.1.0")

# Initialize storage service (local data directory)
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
file_storage = FileStorage(DATA_DIR)


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
