resource "aws_s3_bucket" "file_storage" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy

  tags = {
    Name        = local.bucket_name
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  # Rule 1: Clean up incomplete multipart uploads
  rule {
    id     = "abort-incomplete-mpu"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = var.abort_incomplete_multipart_days
    }
  }

  # Rule 2: Expire old non-current versions
  dynamic "rule" {
    for_each = local.enable_noncurrent_expiration ? [1] : []

    content {
      id     = "expire-old-versions"
      status = "Enabled"

      filter {}

      noncurrent_version_expiration {
        noncurrent_days = var.noncurrent_version_expiration_days
      }
    }
  }

  # Rule 3: Transition raw uploads to STANDARD_IA
  dynamic "rule" {
    for_each = local.enable_raw_ia_transition ? [1] : []

    content {
      id     = "transition-raw-to-standard-ia"
      status = "Enabled"

      filter {
        prefix = "raw/"
      }

      transition {
        storage_class = "STANDARD_IA"
        days          = var.standard_ia_transition_days
      }
    }
  }
}
