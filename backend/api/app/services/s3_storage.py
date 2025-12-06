"""S3-based file storage for uploads, OCR output, and processed text.

This module provides an S3-backed storage implementation that mirrors the
LocalFileStorage interface. Files are organized in the bucket with prefixes:
    - raw/: Original uploaded documents
    - ocr/: Extracted OCR text
    - sentences/: Processed sentence data

The implementation handles AWS credential management flexibly, supporting:
    - Explicit credentials (passed to constructor)
    - AWS CLI default credentials
    - IAM roles (for EC2/ECS deployments)
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

# File type detection constants
PDF_CONTENT_TYPE = "application/pdf"
IMAGE_PREFIX = "image/"
DEFAULT_IMAGE_EXTENSION = ".jpg"


class S3FileStorage:
    """S3-based file storage manager for uploaded documents and derived data."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "eu-west-3",
        aws_profile: str = "",
    ):
        """Initialize S3 storage with bucket and credentials.

        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region where bucket is located
            aws_profile: AWS CLI profile name (optional, e.g., "maxence-dev")
                         If not provided, uses default credential chain:
                         - Environment variables (AWS_PROFILE, AWS_ACCESS_KEY_ID, etc.)
                         - AWS CLI default credentials (~/.aws/credentials)
                         - IAM role (for EC2/ECS instances)
        """
        if not bucket_name:
            raise ValueError("S3 bucket name is required")

        self.bucket_name = bucket_name
        self.region = region

        # Initialize S3 client using AWS profile or default credential chain
        if aws_profile:
            # Use named profile from ~/.aws/credentials
            session = boto3.Session(profile_name=aws_profile)
            self.s3_client = session.client("s3", region_name=region)
        else:
            # Use default credential chain (environment variables, AWS CLI, IAM roles)
            self.s3_client = boto3.client("s3", region_name=region)

        # Verify bucket exists and is accessible at startup
        # This fails fast if there are configuration issues
        self._verify_bucket_exists()

    def _verify_bucket_exists(self) -> None:
        """Verify that the S3 bucket exists and is accessible.

        This method performs a HEAD request to check bucket accessibility without
        listing its contents. It's a lightweight check that fails fast if there are
        permission or configuration issues.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            # Parse the specific error code to provide helpful messages
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                raise ValueError(f"S3 bucket '{self.bucket_name}' does not exist") from e
            if error_code == "403":
                raise ValueError(f"Access denied to S3 bucket '{self.bucket_name}'") from e
            raise ValueError(f"Failed to verify S3 bucket '{self.bucket_name}': {e}") from e

    async def save_uploaded_file(self, file: UploadFile) -> str:
        """Persist an uploaded PDF/image to S3 and return its document ID.

        Files are stored in the 'raw/' prefix with a UUID as the filename.
        Metadata includes the original filename for future reference.
        """
        # Validate content type is provided
        content_type = file.content_type
        if not content_type:
            raise HTTPException(status_code=400, detail="Could not determine file type")

        # Determine file extension based on content type
        extension = self._resolve_extension(file, content_type)

        # Generate unique document ID (UUID v4)
        document_id = str(uuid.uuid4())
        s3_key = f"raw/{document_id}{extension}"

        try:
            # Read the entire file into memory
            # For very large files (>100MB), consider using multipart upload
            file_content = await file.read()

            # Upload to S3 with proper content type and metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "original_filename": file.filename or "",
                    "document_id": document_id,
                },
            )
        except ClientError as exc:
            # S3-specific errors (permissions, quota, etc.)
            raise HTTPException(
                status_code=500, detail=f"Failed to save file to S3: {exc}"
            ) from exc
        except Exception as exc:
            # Generic errors (network, etc.)
            raise HTTPException(status_code=500, detail="Failed to save file") from exc

        return document_id

    def get_raw_file_path(self, document_id: str) -> str | None:
        """Return the S3 key for the raw file if it exists.

        Note: Returns S3 key (string) instead of local Path for S3 storage.
        This maintains interface compatibility with LocalFileStorage.
        """
        document_id = self._validate_document_id(document_id)

        # Try common file extensions to find the uploaded file
        # We don't store the extension separately, so we check each possibility
        # Using HEAD request is efficient - it doesn't download the file
        for ext in [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            s3_key = f"raw/{document_id}{ext}"
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                return s3_key
            except ClientError:
                # File doesn't exist with this extension, try next one
                continue

        # No file found with any supported extension
        return None

    def get_raw_file_content(self, document_id: str) -> bytes:
        """Download and return the raw file content from S3.

        This is used primarily for OCR processing, where we need the actual
        file bytes to process the document.
        """
        # First find the S3 key (with correct extension)
        s3_key = self.get_raw_file_path(document_id)
        if not s3_key:
            raise HTTPException(status_code=404, detail="Document not found")

        try:
            # Download the file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            # Read the streaming body into bytes
            return response["Body"].read()
        except ClientError as exc:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve file from S3: {exc}"
            ) from exc

    def load_ocr_text(self, document_id: str) -> str:
        """Load OCR output text from S3 or raise if it doesn't exist.

        OCR results are stored as UTF-8 encoded text files in the 'ocr/' prefix.
        """
        document_id = self._validate_document_id(document_id)
        s3_key = f"ocr/{document_id}.txt"

        try:
            # Fetch the text file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            # Decode from UTF-8 bytes to string
            return response["Body"].read().decode("utf-8")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                # Provide helpful error message suggesting the required API call
                raise HTTPException(
                    status_code=404,
                    detail="OCR text not found. Run /documents/{id}/ocr first.",
                ) from exc
            # Other S3 errors (permissions, network, etc.)
            raise HTTPException(
                status_code=500, detail=f"Failed to load OCR text from S3: {exc}"
            ) from exc

    def save_ocr_text(self, document_id: str, text: str) -> str:
        """Persist OCR output to S3 for future reuse.

        Stores extracted text as a UTF-8 encoded file in the 'ocr/' prefix.
        This allows sentence processing and vocabulary extraction to be done
        without re-running OCR.
        """
        document_id = self._validate_document_id(document_id)
        s3_key = f"ocr/{document_id}.txt"

        try:
            # Store text with proper encoding and content type
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=text.encode("utf-8"),
                ContentType="text/plain; charset=utf-8",
                Metadata={"document_id": document_id},
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=500, detail=f"Failed to save OCR text to S3: {exc}"
            ) from exc

        return s3_key

    def save_sentences(self, document_id: str, data: Mapping[str, Any]) -> str:
        """Store processed sentence data to S3 for later inspection.

        Sentences are stored as JSON with UTF-8 encoding in the 'sentences/' prefix.
        The ensure_ascii=False preserves Korean characters properly.
        """
        document_id = self._validate_document_id(document_id)
        s3_key = f"sentences/{document_id}.json"

        try:
            # Serialize to JSON with proper Unicode handling
            # ensure_ascii=False preserves Korean and other non-ASCII characters
            json_content = json.dumps(data, ensure_ascii=False, indent=2)

            # Upload JSON with proper content type
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode("utf-8"),
                ContentType="application/json; charset=utf-8",
                Metadata={"document_id": document_id},
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=500, detail=f"Failed to save sentences to S3: {exc}"
            ) from exc

        return s3_key

    def load_sentences(self, document_id: str) -> dict[str, Any]:
        """Load stored sentence data from S3 if available.

        Returns the parsed JSON data containing sentences and metadata.
        """
        document_id = self._validate_document_id(document_id)
        s3_key = f"sentences/{document_id}.json"

        try:
            # Download JSON file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response["Body"].read().decode("utf-8")
            # Parse JSON and return as dictionary
            return json.loads(content)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                # Provide helpful error message
                raise HTTPException(
                    status_code=404,
                    detail="No sentence data found. Run /documents/{id}/sentences first.",
                ) from exc
            # Other S3 errors
            raise HTTPException(
                status_code=500, detail=f"Failed to load sentences from S3: {exc}"
            ) from exc

    def _validate_document_id(self, document_id: str) -> str:
        """Ensure the supplied document ID is a canonical UUID string.

        This prevents path traversal attacks and ensures consistent formatting.
        UUIDs are validated and normalized to lowercase hyphenated format.
        """
        try:
            # Validate and normalize the UUID
            # This will raise ValueError if the string is not a valid UUID
            validated = uuid.UUID(str(document_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid document_id format.") from exc

        # Return normalized UUID string (lowercase with hyphens)
        return str(validated)

    def _resolve_extension(self, file: UploadFile, content_type: str) -> str:
        """Determine the file extension for an upload based on its metadata.

        Priority:
        1. Use .pdf for PDF content type
        2. For images, use original filename extension if available
        3. Fall back to .jpg for images without extension
        """
        # PDFs are straightforward
        if content_type == PDF_CONTENT_TYPE:
            return ".pdf"

        # Images: try to preserve the original extension
        if content_type.startswith(IMAGE_PREFIX):
            if file.filename:
                # Extract extension from original filename
                suffix = Path(file.filename).suffix
                if suffix:
                    return suffix
            # No extension in filename, use default
            return DEFAULT_IMAGE_EXTENSION

        # Unsupported file type
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Only images and PDFs are supported.",
        )
