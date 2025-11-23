"""Service exports for the OCRean backend."""

from .files import FileStorage
from .ocr import OCRProcessor
from .text import TextProcessor

__all__ = ["FileStorage", "OCRProcessor", "TextProcessor"]
