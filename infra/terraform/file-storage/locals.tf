locals {
  bucket_name                  = var.bucket_name != "" ? var.bucket_name : "${var.project}-${var.environment}-files"
  enable_noncurrent_expiration = var.enable_versioning && var.noncurrent_version_expiration_days > 0
  enable_raw_ia_transition     = var.standard_ia_transition_days > 0
}
