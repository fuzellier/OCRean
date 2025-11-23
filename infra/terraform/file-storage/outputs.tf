output "file_storage_bucket_name" {
  description = "Name of the S3 bucket storing uploads, OCR output, and processed text."
  value       = aws_s3_bucket.file_storage.bucket
}

output "file_storage_bucket_arn" {
  description = "ARN of the S3 file storage bucket."
  value       = aws_s3_bucket.file_storage.arn
}
