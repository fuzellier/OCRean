"""Service exports for the OCRean backend."""

from .files import LocalFileStorage
from .ocr import OCRProcessor
from .s3_storage import S3FileStorage
from .storage import FileStorage, create_storage
from .text import TextProcessor

__all__ = [
    "LocalFileStorage",
    "S3FileStorage",
    "FileStorage",
    "create_storage",
    "OCRProcessor",
    "TextProcessor",
]
