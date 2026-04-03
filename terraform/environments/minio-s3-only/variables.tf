variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_access_key_id" {
  type      = string
  default   = "minioadmin"
  sensitive = true
}

variable "aws_secret_access_key" {
  type      = string
  default   = "minioadmin"
  sensitive = true
}

variable "s3_endpoint_url" {
  type        = string
  description = "MinIO S3 API (e.g. http://localhost:9000)."
  default     = "http://localhost:9000"
}

variable "name_prefix" {
  type    = string
  default = "probe"
}
