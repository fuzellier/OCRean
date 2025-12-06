"""Service exports for the OCRean backend."""

from .files import LocalFileStorage
from .ocr import OCRProcessor
from .s3_storage import S3FileStorage
from .text import TextProcessor

__all__ = ["LocalFileStorage", "OCRProcessor", "TextProcessor", "S3FileStorage"]
