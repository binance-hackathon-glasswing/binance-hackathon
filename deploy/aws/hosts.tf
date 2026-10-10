resource "aws_iam_role" "host" {
  for_each = local.hosts
  name     = "${var.name}-${each.key}"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }
  ] })
}
resource "aws_iam_instance_profile" "host" {
  for_each = local.hosts
  name     = "${var.name}-${each.key}"
  role     = aws_iam_role.host[each.key].name
}
# Secret metadata only. Values are provisioned outside Terraform and never in state.
resource "aws_secretsmanager_secret" "service" {
  for_each                = toset(["signer", "uploader", "evidence"])
  name                    = "${var.name}/${each.key}"
  description             = "Separate ${each.key} credentials; no values managed by Terraform"
  recovery_window_in_days = 30
  lifecycle { prevent_destroy = true }
}
resource "aws_iam_role_policy" "host" {
  for_each = local.hosts
  role     = aws_iam_role.host[each.key].id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"], Resource = "${aws_s3_bucket.artifacts.arn}/releases/*" },
    { Effect = "Allow", Action = ["kms:Decrypt"], Resource = aws_kms_key.data.arn, Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } } },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.host[each.key].arn}:*" },
    { Effect = "Allow", Action = ["cloudwatch:PutMetricData"], Resource = "*", Condition = { StringEquals = { "cloudwatch:namespace" = "LARP/Runtime" } } }
    ], contains(local.db_hosts, each.key) ? [
    { Effect = "Allow", Action = ["rds-db:connect"], Resource = "arn:aws:rds-db:${var.region}:${var.account_id}:dbuser:${aws_db_instance.larp.resource_id}/larp_${each.key}" }
    ] : [], contains(["signer", "uploader", "evidence"], each.key) ? [
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.service[each.key].arn }
    ] : [], [for statement in [
      { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectRetention", "s3:PutObjectRetention"], Resource = "${aws_s3_bucket.archive.arn}/archive/*" },
      { Effect = "Allow", Action = ["kms:GenerateDataKey"], Resource = aws_kms_key.data.arn, Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } } }
  ] : statement if each.key == "archive"]) })
}
resource "aws_iam_role_policy_attachment" "development_ssm" {
  for_each   = var.enable_development_ssm ? local.hosts : toset([])
  role       = aws_iam_role.host[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  lifecycle {
    precondition {
      condition     = var.environment == "development"
      error_message = "Interactive SSM access is permitted by this template only in development."
    }
  }
}
resource "aws_instance" "host" {
  for_each                    = var.enable_hosts ? local.hosts : toset([])
  ami                         = var.ami_id
  instance_type               = var.host_instance_type
  subnet_id                   = aws_subnet.private[each.key == "standby" ? 1 : 0].id
  vpc_security_group_ids      = [aws_security_group.host[each.key].id]
  iam_instance_profile        = aws_iam_instance_profile.host[each.key].name
  associate_public_ip_address = false
  disable_api_termination     = true
  monitoring                  = true
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }
  root_block_device {
    encrypted   = true
    kms_key_id  = aws_kms_key.data.arn
    volume_type = "gp3"
    volume_size = 20
  }
  # Image and release provisioning are separate. Never fetch/execute mutable code
  # or start a signer, trading process, or promotion script from user-data.
  user_data = "#cloud-config\nwrite_files:\n  - path: /etc/larp-host-role\n    permissions: '0444'\n    content: '${each.key}'\n"
  tags      = { Name = "${var.name}-${each.key}", Role = each.key }
  lifecycle {
    precondition {
      condition     = var.ami_id != null && can(regex("^ami-[a-f0-9]+$", var.ami_id))
      error_message = "Select a reviewed immutable Linux AMI before enabling hosts."
    }
  }
}
