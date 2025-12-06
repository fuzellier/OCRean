"""Storage backends for document management."""

from .factory import create_storage
from .local import LocalFileStorage
from .protocol import FileStorage
from .s3 import S3FileStorage

__all__ = [
    "FileStorage",
    "LocalFileStorage",
    "S3FileStorage",
    "create_storage",
]
