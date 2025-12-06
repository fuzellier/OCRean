"""Tests for LocalFileStorage document ID validation."""

import pytest
from fastapi import HTTPException

from services.files import LocalFileStorage


def test_load_ocr_text_rejects_invalid_document_id(tmp_path):
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(HTTPException) as excinfo:
        storage.load_ocr_text("../etc/passwd")

    assert excinfo.value.status_code == 400
    assert "document_id" in excinfo.value.detail
