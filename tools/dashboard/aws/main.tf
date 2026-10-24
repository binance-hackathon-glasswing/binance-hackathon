# IDEA-091: hourly Lambda -> private S3 -> CloudFront with a login. The Lambda can run only the two read-only SSM
# documents below, only on the primary; the bucket is reachable only through this distribution.
locals {
  decisions_document = "${var.name}-dashboard-decisions-export"
  tx_document        = "${var.name}-dashboard-tx-export"
  document_arns = [for d in [local.decisions_document, local.tx_document] :
  "arn:aws:ssm:${var.region}:${var.account_id}:document/${d}"]
  primary_arn = "arn:aws:ec2:${var.region}:${var.account_id}:instance/${var.primary_instance_id}"
  bucket_arn  = "arn:aws:s3:::${var.bucket_name}"
  # The SSM document body is the script itself; `set --` passes the document parameter as its first argument.
  decisions_lines = concat(["set -- {{ limit }}"], split("\n", trimspace(file("${path.module}/../decisions-export.sh"))))
  tx_lines        = split("\n", trimspace(file("${path.module}/../tx-export.sh")))
  lambda_policy = {
    Version = "2012-10-17"
    Statement = concat([
      { Sid = "Logs", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource = ["${aws_cloudwatch_log_group.dashboard.arn}:*"] },
      { Sid = "ListState", Effect = "Allow", Action = ["s3:ListBucket"], Resource = [local.bucket_arn],
      Condition = { StringLike = { "s3:prefix" = ["state/*"] } } },
      { Sid = "State", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["${local.bucket_arn}/state/*"] },
      { Sid = "Site", Effect = "Allow", Action = ["s3:PutObject"], Resource = ["${local.bucket_arn}/site/*"] },
      { Sid = "ReadOnlyExports", Effect = "Allow", Action = ["ssm:SendCommand"],
      Resource = concat(local.document_arns, [local.primary_arn]) },
      { Sid = "ExportResults", Effect = "Allow", Action = ["ssm:GetCommandInvocation"], Resource = ["*"] },
      ], var.web3_secret_arn == null ? [] : [
      { Sid = "Web3ReadOnlyKey", Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [var.web3_secret_arn] }
    ])
  }
}

# --- storage: private, owner-enforced, encrypted; CloudFront only -----------------------------------------------------
resource "aws_s3_bucket" "dashboard" {
  bucket = var.bucket_name
}
resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket                  = aws_s3_bucket.dashboard.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_ownership_controls" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  rule { object_ownership = "BucketOwnerEnforced" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "CloudFrontReadsTheSiteOnly"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${local.bucket_arn}/site/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.dashboard.arn } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.dashboard]
}

# --- viewing: CloudFront with a login checked against a KeyValueStore hash set outside Terraform -------------------------
resource "aws_cloudfront_origin_access_control" "dashboard" {
  name                              = "${var.name}-dashboard"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}
resource "aws_cloudfront_key_value_store" "auth" {
  name    = "${var.name}-dashboard-auth"
  comment = "IDEA-091: basic-auth-sha256, set by an operator; never in Terraform"
}
resource "aws_cloudfront_function" "viewer_auth" {
  name                         = "${var.name}-dashboard-auth"
  runtime                      = "cloudfront-js-2.0"
  publish                      = true
  code                         = file("${path.module}/viewer-auth.js")
  key_value_store_associations = [aws_cloudfront_key_value_store.auth.arn]
}
resource "aws_cloudfront_distribution" "dashboard" {
  enabled             = true
  comment             = "IDEA-091 LARP dashboard (private)"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  origin {
    origin_id                = "site"
    domain_name              = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_path              = "/site"
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
  }
  default_cache_behavior {
    target_origin_id       = "site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # managed CachingDisabled: always the latest page
    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.viewer_auth.arn
    }
  }
  restrictions {
    geo_restriction { restriction_type = "none" }
  }
  viewer_certificate { cloudfront_default_certificate = true }
}

# --- the two read-only exports, as fixed SSM documents ----------------------------------------------------------------
resource "aws_ssm_document" "decisions" {
  name          = local.decisions_document
  document_type = "Command"
  content = jsonencode({
    schemaVersion = "2.2"
    description   = "IDEA-087/091: read-only decisions export for the dashboard"
    parameters    = { limit = { type = "String", default = "40", allowedPattern = "^[0-9]{1,3}$" } }
    mainSteps     = [{ action = "aws:runShellScript", name = "export", inputs = { runCommand = local.decisions_lines } }]
  })
}
resource "aws_ssm_document" "tx" {
  name          = local.tx_document
  document_type = "Command"
  content = jsonencode({
    schemaVersion = "2.2"
    description   = "IDEA-087/091: read-only transaction hashes for seeding the chain monitor"
    mainSteps     = [{ action = "aws:runShellScript", name = "export", inputs = { runCommand = local.tx_lines } }]
  })
}

# --- the Lambda and its hourly schedule -------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/aws/lambda/${var.name}-dashboard"
  retention_in_days = var.log_retention_days
}
resource "aws_iam_role" "lambda" {
  name = "${var.name}-dashboard-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy" "lambda" {
  name   = "dashboard"
  role   = aws_iam_role.lambda.id
  policy = jsonencode(local.lambda_policy)
}
resource "aws_lambda_function" "dashboard" {
  function_name                  = "${var.name}-dashboard"
  role                           = aws_iam_role.lambda.arn
  runtime                        = "python3.12"
  handler                        = "tools.dashboard.aws.handler.lambda_handler"
  filename                       = var.package_path
  source_code_hash               = filebase64sha256(var.package_path)
  timeout                        = 300
  memory_size                    = 512
  reserved_concurrent_executions = 1
  environment {
    variables = merge({
      BUCKET              = aws_s3_bucket.dashboard.id
      PRIMARY_INSTANCE_ID = var.primary_instance_id
      DECISIONS_DOCUMENT  = aws_ssm_document.decisions.name
      TX_DOCUMENT         = aws_ssm_document.tx.name
      WALLET              = lower(var.wallet)
      START_NONCE         = tostring(var.start_nonce)
      START_USDT          = tostring(var.start_usdt)
    }, var.web3_secret_arn == null ? {} : { WEB3_SECRET_ARN = var.web3_secret_arn })
  }
  depends_on = [aws_cloudwatch_log_group.dashboard]
}
resource "aws_iam_role" "scheduler" {
  name = "${var.name}-dashboard-scheduler"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "scheduler.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy" "scheduler" {
  name = "invoke-dashboard"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "lambda:InvokeFunction", Resource = aws_lambda_function.dashboard.arn }]
  })
}
resource "aws_scheduler_schedule" "hourly" {
  name                = "${var.name}-dashboard-hourly"
  schedule_expression = "rate(1 hour)"
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_lambda_function.dashboard.arn
    role_arn = aws_iam_role.scheduler.arn
    retry_policy { maximum_retry_attempts = 0 } # the next hour runs anyway; a failed run changes nothing
  }
}
