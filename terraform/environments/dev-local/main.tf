provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key_id
  secret_key                  = var.aws_secret_access_key
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id   = true

  dynamic "endpoints" {
    for_each = var.aws_endpoint_url != "" ? [var.aws_endpoint_url] : []
    content {
      s3              = endpoints.value
      events          = endpoints.value
      cognitoidp      = endpoints.value
      ses             = endpoints.value
      sesv2           = endpoints.value
      sqs             = endpoints.value
      sns             = endpoints.value
      dynamodb        = endpoints.value
      secretsmanager  = endpoints.value
      ssm             = endpoints.value
      kms             = endpoints.value
      sts             = endpoints.value
    }
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "probe" {
  bucket = "${var.name_prefix}-bucket-${random_id.suffix.hex}"
}

resource "aws_cloudwatch_event_bus" "probe" {
  name = "${var.name_prefix}-bus-${random_id.suffix.hex}"
}

resource "aws_cognito_user_pool" "probe" {
  name = "${var.name_prefix}-pool-${random_id.suffix.hex}"
}

resource "aws_cognito_user_pool_client" "probe" {
  name         = "${var.name_prefix}-client"
  user_pool_id = aws_cognito_user_pool.probe.id

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}

resource "aws_sesv2_email_identity" "probe" {
  email_identity = var.ses_email
}

resource "aws_sqs_queue" "probe" {
  name = "${var.name_prefix}-queue-${random_id.suffix.hex}"
}

resource "aws_sns_topic" "probe" {
  name = "${var.name_prefix}-topic-${random_id.suffix.hex}"
}

resource "aws_dynamodb_table" "probe" {
  name         = "${var.name_prefix}-ddb-${random_id.suffix.hex}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }
}

resource "aws_secretsmanager_secret" "probe" {
  name = "${var.name_prefix}-secret-${random_id.suffix.hex}"
}

resource "aws_secretsmanager_secret_version" "probe" {
  secret_id     = aws_secretsmanager_secret.probe.id
  secret_string = jsonencode({ probe = "terraform" })
}

resource "aws_ssm_parameter" "probe" {
  name  = "/${var.name_prefix}/param-${random_id.suffix.hex}"
  type  = "String"
  value = "probe"
}
