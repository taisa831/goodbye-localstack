output "s3_bucket_name" {
  value = aws_s3_bucket.probe.bucket
}

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.probe.name
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.probe.id
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.probe.id
}

output "ses_email_identity" {
  value = aws_sesv2_email_identity.probe.email_identity
}

output "sqs_queue_url" {
  value = aws_sqs_queue.probe.url
}

output "sns_topic_arn" {
  value = aws_sns_topic.probe.arn
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.probe.name
}

output "secretsmanager_secret_arn" {
  value = aws_secretsmanager_secret.probe.arn
}

output "ssm_parameter_name" {
  value = aws_ssm_parameter.probe.name
}
