output "dashboard_url" { value = "https://${aws_cloudfront_distribution.dashboard.domain_name}/" }
output "auth_key_value_store_arn" { value = aws_cloudfront_key_value_store.auth.arn }
output "lambda_function_name" { value = aws_lambda_function.dashboard.function_name }
