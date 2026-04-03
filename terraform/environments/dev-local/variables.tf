variable "aws_region" {
  type        = string
  description = "AWS region passed to the provider and resources."
  default     = "us-east-1"
}

variable "aws_access_key_id" {
  type        = string
  description = "Static credentials for emulator (not for production)."
  default     = "test"
  sensitive   = true
}

variable "aws_secret_access_key" {
  type        = string
  description = "Static credentials for emulator (not for production)."
  default     = "test"
  sensitive   = true
}

variable "aws_endpoint_url" {
  type        = string
  description = "Custom endpoint for S3, EventBridge (events), Cognito IDP, and SES. Empty = real AWS (use with care)."
  default     = ""
}

variable "name_prefix" {
  type        = string
  description = "Prefix for named resources."
  default     = "probe"
}

variable "ses_email" {
  type        = string
  description = "Email for aws_ses_email_identity (must match what the emulator accepts)."
  default     = "probe@example.com"
}
