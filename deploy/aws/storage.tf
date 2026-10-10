resource "aws_kms_key" "data" {
  description             = "${var.name} database, archive and release encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket" "archive" {
  bucket              = var.archive_bucket_name
  object_lock_enabled = true
  force_destroy       = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "archive" {
  bucket = aws_s3_bucket.archive.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_object_lock_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.archive_retention_days
    }
  }
  depends_on = [aws_s3_bucket_versioning.archive]
}
resource "aws_s3_bucket" "artifacts" {
  bucket        = var.artifact_bucket_name
  force_destroy = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}
locals {
  buckets = { archive = aws_s3_bucket.archive, artifacts = aws_s3_bucket.artifacts }
}
resource "aws_s3_bucket_public_access_block" "all" {
  for_each                = local.buckets
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = local.buckets
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
    bucket_key_enabled = true
  }
}
resource "aws_s3_bucket_policy" "all" {
  for_each = local.buckets
  bucket   = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Sid = "TLSOnly", Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [each.value.arn, "${each.value.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }
    ], each.key == "archive" ? [
    { Sid = "NoDeletion", Effect = "Deny", Principal = "*", Action = ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:BypassGovernanceRetention"], Resource = "${each.value.arn}/*" },
    { Sid = "ConditionalCreation", Effect = "Deny", Principal = "*", Action = "s3:PutObject", Resource = "${each.value.arn}/*", Condition = { Null = { "s3:if-none-match" = "true" }, Bool = { "s3:ObjectCreationOperation" = "true" } } }
  ] : []) })
}
resource "aws_db_subnet_group" "larp" {
  name       = var.name
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_db_parameter_group" "larp" {
  name_prefix = "${var.name}-"
  family      = var.postgres_family
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}
resource "aws_db_instance" "larp" {
  identifier                      = var.name
  engine                          = "postgres"
  engine_version                  = var.postgres_version
  instance_class                  = var.db_instance_class
  allocated_storage               = var.db_storage_gib
  max_allocated_storage           = var.db_max_storage_gib
  storage_type                    = "gp3"
  storage_encrypted               = true
  kms_key_id                      = aws_kms_key.data.arn
  db_name                         = "larp"
  username                        = "larp_admin"
  manage_master_user_password     = true
  iam_database_authentication_enabled = true
  db_subnet_group_name            = aws_db_subnet_group.larp.name
  parameter_group_name            = aws_db_parameter_group.larp.name
  vpc_security_group_ids          = [aws_security_group.database.id]
  publicly_accessible            = false
  multi_az                       = var.multi_az
  backup_retention_period        = var.backup_retention_days
  deletion_protection            = true
  skip_final_snapshot            = false
  final_snapshot_identifier      = "${var.name}-final"
  auto_minor_version_upgrade     = false
  apply_immediately              = false
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  copy_tags_to_snapshot           = true
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.db_max_storage_gib >= var.db_storage_gib
      error_message = "Maximum storage must cover allocated storage."
    }
  }
}
