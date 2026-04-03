provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key_id
  secret_key                  = var.aws_secret_access_key
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id   = true

  endpoints {
    s3 = var.s3_endpoint_url
  }

  s3_use_path_style = true
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "probe" {
  bucket = "${var.name_prefix}-bucket-${random_id.suffix.hex}"
}
