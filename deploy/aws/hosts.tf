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
# Secret metadata only. Values are provisioned outside Terraform and never in state. `runtime` holds the coordinator's
# public wallet address and Web3 market-data key pair only (IDEA-042 S3/S4). The wallet key is not a managed
# secret: it is a root-only file on the signer's encrypted disk (IDEA-046 B2), so the signer reads no secret.
locals {
  # Which hosts may read which secret: each secret has its own readers, nothing else. One IAM role on `primary`
  # can read both (IDEA-046 B1 trade-off); each service still loads only its own secret ID. The evidence poller
  # needs no key and cannot reach instance metadata, so it has no secret (#61).
  secret_readers = { uploader = ["primary"], runtime = ["primary"] }
  # Provisioned SQL roles are service identities, not EC2 host names. SQL grants, not IAM, separate the roles
  # that share `primary` (IDEA-045, IDEA-046).
  db_users = {
    primary = ["larp_runtime", "larp_execution", "larp_archive", "larp_uploader"]
    signer  = ["larp_signer"]
  }
}
resource "aws_secretsmanager_secret" "service" {
  for_each                = toset(keys(local.secret_readers))
  name                    = "${var.name}/${each.key}"
  description             = "Separate ${each.key} credentials; no values managed by Terraform"
  recovery_window_in_days = 30
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
    { Effect = "Allow", Action = ["rds-db:connect"], Resource = [for user in local.db_users[each.key] : "arn:aws:rds-db:${var.region}:${var.account_id}:dbuser:${aws_db_instance.larp.resource_id}/${user}"] }
    ] : [], [for secret, readers in local.secret_readers :
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.service[secret].arn }
    if contains(readers, each.key)
    ], [for statement in [
      { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectRetention", "s3:PutObjectRetention"], Resource = "${aws_s3_bucket.archive.arn}/archive/*" },
      { Effect = "Allow", Action = ["kms:GenerateDataKey"], Resource = aws_kms_key.data.arn, Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } } }
  ] : statement if each.key == "primary"]) })
}
resource "aws_iam_role_policy_attachment" "development_ssm" {
  # Only primary can reach Systems Manager. The isolated signer needs a separate provisioning decision.
  for_each   = var.enable_development_ssm ? toset(["primary"]) : toset([])
  role       = aws_iam_role.host[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  lifecycle {
    precondition {
      condition     = var.environment == "development"
      error_message = "Interactive SSM access is permitted by this template only in development."
    }
    precondition {
      condition     = var.enable_external_https
      error_message = "Development SSM requires primary HTTPS egress; it never enables signer access."
    }
  }
}
resource "aws_instance" "host" {
  for_each                    = var.enable_hosts ? local.hosts : toset([])
  ami                         = var.ami_id
  instance_type               = var.host_instance_types[each.key]
  subnet_id                   = each.key == "primary" ? aws_subnet.public.id : aws_subnet.private[0].id
  vpc_security_group_ids      = [aws_security_group.host[each.key].id]
  iam_instance_profile        = aws_iam_instance_profile.host[each.key].name
  associate_public_ip_address = contains(local.external, each.key)
  disable_api_termination     = !var.allow_teardown
  # Basic five-minute metrics are free; status checks and recovery do not need detailed monitoring.
  monitoring = false
  # Never bill CPU above the burst baseline (IDEA-046 B4); a sustained load is throttled instead.
  credit_specification {
    cpu_credits = "standard"
  }
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
