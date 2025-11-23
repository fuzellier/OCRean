"""Minimal FastAPI application placeholder."""

from fastapi import FastAPI

app = FastAPI(title="OCRean API", version="0.1.0")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello, World!"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
