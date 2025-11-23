variable "aws_region" {
  description = "AWS region where the file storage resources will be created."
  type        = string
  default     = "eu-west-3"
}

variable "project" {
  description = "Project name used for resource naming and tagging."
  type        = string
  default     = "ocrean"
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)."
  type        = string
  default     = "dev"
}

variable "bucket_name" {
  description = "Optional override for the S3 bucket name. Leave empty to auto-generate."
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Allow Terraform to delete non-empty buckets. Use with care."
  type        = bool
  default     = false
}

variable "enable_versioning" {
  description = "Enable S3 object versioning for the file storage bucket."
  type        = bool
  default     = true
}

variable "abort_incomplete_multipart_days" {
  description = "Number of days before aborting incomplete multipart uploads."
  type        = number
  default     = 7
}

variable "noncurrent_version_expiration_days" {
  description = "Days to retain noncurrent object versions. Ignored if versioning is disabled."
  type        = number
  default     = 30
}

variable "standard_ia_transition_days" {
  description = "Days before transitioning raw uploads to STANDARD_IA storage. Set to 0 to disable."
  type        = number
  default     = 30
}
