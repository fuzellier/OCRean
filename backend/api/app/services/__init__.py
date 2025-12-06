"""Service exports for the OCRean backend."""

from .processing import OCRProcessor, TextProcessor
from .storage import FileStorage, LocalFileStorage, S3FileStorage, create_storage

__all__ = [
    "FileStorage",
    "LocalFileStorage",
    "S3FileStorage",
    "create_storage",
    "OCRProcessor",
    "TextProcessor",
]
