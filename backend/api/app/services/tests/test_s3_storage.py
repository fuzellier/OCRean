"""Tests for S3FileStorage."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

from services.storage import S3FileStorage


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch("services.s3_storage.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        # Mock head_bucket to succeed by default
        mock_client.head_bucket.return_value = {}
        yield mock_client


def test_s3_storage_initialization(mock_s3_client):
    """Test S3FileStorage initializes correctly."""
    storage = S3FileStorage(
        bucket_name="test-bucket",
        region="eu-west-3",
    )

    assert storage.bucket_name == "test-bucket"
    assert storage.region == "eu-west-3"
    mock_s3_client.head_bucket.assert_called_once_with(Bucket="test-bucket")


def test_s3_storage_requires_bucket_name(mock_s3_client):
    """Test that bucket name is required."""
    with pytest.raises(ValueError, match="bucket name is required"):
        S3FileStorage(bucket_name="")


def test_s3_storage_bucket_not_found(mock_s3_client):
    """Test handling of non-existent bucket."""
    error = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")
    mock_s3_client.head_bucket.side_effect = error

    with pytest.raises(ValueError, match="does not exist"):
        S3FileStorage(bucket_name="nonexistent-bucket")


def test_s3_storage_bucket_access_denied(mock_s3_client):
    """Test handling of access denied error."""
    error = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket")
    mock_s3_client.head_bucket.side_effect = error

    with pytest.raises(ValueError, match="Access denied"):
        S3FileStorage(bucket_name="forbidden-bucket")


def test_validate_document_id_rejects_invalid(mock_s3_client):
    """Test document ID validation."""
    storage = S3FileStorage(bucket_name="test-bucket")

    with pytest.raises(HTTPException) as excinfo:
        storage._validate_document_id("../etc/passwd")

    assert excinfo.value.status_code == 400
    assert "document_id" in excinfo.value.detail


def test_save_ocr_text_uses_correct_key(mock_s3_client):
    """Test that OCR text is saved with correct S3 key."""
    storage = S3FileStorage(bucket_name="test-bucket")
    document_id = "123e4567-e89b-12d3-a456-426614174000"

    storage.save_ocr_text(document_id, "Test OCR text")

    mock_s3_client.put_object.assert_called_once()
    call_kwargs = mock_s3_client.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["Key"] == f"ocr/{document_id}.txt"
    assert call_kwargs["Body"] == b"Test OCR text"


def test_load_ocr_text_not_found(mock_s3_client):
    """Test loading non-existent OCR text."""
    error = ClientError({"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "GetObject")
    mock_s3_client.get_object.side_effect = error

    storage = S3FileStorage(bucket_name="test-bucket")
    document_id = "123e4567-e89b-12d3-a456-426614174000"

    with pytest.raises(HTTPException) as excinfo:
        storage.load_ocr_text(document_id)

    assert excinfo.value.status_code == 404
    assert "OCR text not found" in excinfo.value.detail


def test_get_raw_file_path_finds_pdf(mock_s3_client):
    """Test finding a PDF file in S3."""
    storage = S3FileStorage(bucket_name="test-bucket")
    document_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock head_object to succeed for PDF
    def head_object_side_effect(Bucket, Key):
        if Key.endswith(".pdf"):
            return {"ContentLength": 1000}
        raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")

    mock_s3_client.head_object.side_effect = head_object_side_effect

    result = storage.get_raw_file_path(document_id)

    assert result == f"raw/{document_id}.pdf"


def test_get_raw_file_path_not_found(mock_s3_client):
    """Test when raw file is not found."""
    storage = S3FileStorage(bucket_name="test-bucket")
    document_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock head_object to always fail
    error = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
    mock_s3_client.head_object.side_effect = error

    result = storage.get_raw_file_path(document_id)

    assert result is None
