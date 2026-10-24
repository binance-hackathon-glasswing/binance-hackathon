# IDEA-092 A2-A4, offline: a mocked AWS provider, plan only. Run from tools/dashboard/aws: terraform init -backend=false
# && terraform test.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_cloudfront_distribution" {
    defaults = { arn = "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE", domain_name = "d111111abcdef8.cloudfront.net" }
  }
  mock_resource "aws_cloudfront_key_value_store" {
    defaults = { arn = "arn:aws:cloudfront::123456789012:key-value-store/0a1b2c3d-example" }
  }
  mock_resource "aws_cloudfront_function" {
    defaults = { arn = "arn:aws:cloudfront::123456789012:function/larp-dev-dashboard-auth" }
  }
  mock_resource "aws_lambda_function" {
    defaults = { arn = "arn:aws:lambda:ap-southeast-2:123456789012:function:larp-dev-dashboard" }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-southeast-2:123456789012:log-group:/aws/lambda/larp-dev-dashboard" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/larp-dev-dashboard" }
  }
}

variables {
  account_id          = "123456789012"
  region              = "ap-southeast-2"
  environment         = "development"
  name                = "larp-dev"
  bucket_name         = "larp-dev-dashboard-example"
  primary_instance_id = "i-0123456789abcdef0"
  wallet              = "0x1111111111111111111111111111111111111111"
  start_nonce         = 4
  start_usdt          = 96
  package_path        = "viewer-auth.js" # any existing file stands in for the package in a plan
  log_retention_days  = 30
}

run "a2_ssm_least_privilege" {
  command = plan
  assert {
    condition = toset(one([for s in jsondecode(aws_iam_role_policy.lambda.policy).Statement : s.Resource if contains(s.Action, "ssm:SendCommand")])) == toset([
      "arn:aws:ssm:ap-southeast-2:123456789012:document/larp-dev-dashboard-decisions-export",
      "arn:aws:ssm:ap-southeast-2:123456789012:document/larp-dev-dashboard-tx-export",
      "arn:aws:ec2:ap-southeast-2:123456789012:instance/i-0123456789abcdef0",
    ])
    error_message = "ssm:SendCommand must be limited to the two export documents and the primary."
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.lambda.policy, "AWS-RunShellScript") && !strcontains(aws_iam_role_policy.lambda.policy, "\"*\",\"Sid\":\"ReadOnlyExports\"")
    error_message = "The Lambda must not be able to run arbitrary shell commands."
  }
  assert {
    condition     = length([for s in jsondecode(aws_iam_role_policy.lambda.policy).Statement : s if contains(s.Action, "secretsmanager:GetSecretValue")]) == 0
    error_message = "Without a Web3 secret the Lambda reads no secret."
  }
  assert {
    condition     = jsondecode(aws_ssm_document.decisions.content).mainSteps[0].inputs.runCommand[0] == "set -- {{ limit }} {{ since }}"
    error_message = "The decisions document passes its limit and cursor as the script's arguments."
  }
}

run "a3_private_bucket_and_login" {
  command = plan
  assert {
    condition = alltrue([aws_s3_bucket_public_access_block.dashboard.block_public_acls, aws_s3_bucket_public_access_block.dashboard.block_public_policy,
    aws_s3_bucket_public_access_block.dashboard.ignore_public_acls, aws_s3_bucket_public_access_block.dashboard.restrict_public_buckets])
    error_message = "The bucket must block all public access."
  }
  assert {
    condition     = jsondecode(aws_s3_bucket_policy.dashboard.policy).Statement[0].Principal.Service == "cloudfront.amazonaws.com" && length(jsondecode(aws_s3_bucket_policy.dashboard.policy).Statement) == 1
    error_message = "Only CloudFront may read the bucket."
  }
  assert {
    condition     = one(aws_cloudfront_distribution.dashboard.default_cache_behavior[0].function_association).event_type == "viewer-request"
    error_message = "Every viewer request must pass the login function."
  }
  assert {
    condition     = aws_cloudfront_distribution.dashboard.default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https"
    error_message = "The login travels over HTTPS only."
  }
}

run "a4_hourly_single_short_runs" {
  command = plan
  assert {
    condition     = aws_scheduler_schedule.hourly.schedule_expression == "rate(1 hour)"
    error_message = "The refresh runs hourly."
  }
  assert {
    condition     = aws_lambda_function.dashboard.reserved_concurrent_executions == 1 && aws_lambda_function.dashboard.timeout <= 300
    error_message = "One run at a time, at most 300 s."
  }
}

run "a2_web3_secret_is_the_only_secret" {
  command = plan
  variables {
    web3_secret_arn = "arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:larp-web3-readonly-AbCdEf"
  }
  assert {
    condition = one([for s in jsondecode(aws_iam_role_policy.lambda.policy).Statement : s.Resource if contains(s.Action, "secretsmanager:GetSecretValue")]) == [
    "arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:larp-web3-readonly-AbCdEf"]
    error_message = "The Lambda may read only the configured read-only Web3 key."
  }
}
