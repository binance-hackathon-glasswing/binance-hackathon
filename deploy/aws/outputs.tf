output "database_host" { value = aws_db_instance.larp.address }
output "database_name" { value = aws_db_instance.larp.db_name }
output "database_admin_secret_arn" {
  description = "Nonsecret reference for provisioning only; never give its value to runtime hosts."
  value       = aws_db_instance.larp.master_user_secret[0].secret_arn
}
output "archive_bucket" { value = aws_s3_bucket.archive.id }
output "artifact_bucket" { value = aws_s3_bucket.artifacts.id }
output "archive_kms_key" { value = aws_kms_key.data.arn }
output "service_secret_arns" { value = { for name, secret in aws_secretsmanager_secret.service : name => secret.arn } }
output "host_ids" { value = { for name, host in aws_instance.host : name => host.id } }
output "private_subnets" { value = aws_subnet.private[*].id }
output "signing_enabled" { value = false }
