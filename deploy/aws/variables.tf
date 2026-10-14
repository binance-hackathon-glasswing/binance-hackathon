variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Select the target AWS account explicitly."
  }
}
variable "region" { type = string }
variable "availability_zones" {
  type = list(string)
  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Select two distinct availability zones in the target region."
  }
}
variable "environment" {
  type = string
  validation {
    condition     = contains(["development", "rehearsal", "final"], var.environment)
    error_message = "Use a separate development, rehearsal or final stack."
  }
}
variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.name))
    error_message = "Use a short lowercase resource prefix."
  }
}
variable "vpc_cidr" { type = string }
variable "archive_bucket_name" { type = string }
variable "artifact_bucket_name" { type = string }
variable "archive_retention_days" {
  type = number
  validation {
    condition     = var.archive_retention_days >= 1 && floor(var.archive_retention_days) == var.archive_retention_days
    error_message = "Choose the explicit immutable archive retention in whole days."
  }
  # IDEA-036 #1: anchors and backups are kept at least through the whole of 2026-12-31 (audit and technical
  # review). An object written on Oct 11 with 81 days unlocks during Dec 31, so 82 (IDEA-042 V9). COMPLIANCE
  # retention can never be shortened afterwards.
  validation {
    condition     = var.archive_retention_days >= 82
    error_message = "Archive retention must cover all of 2026-12-31: 82 days or more."
  }
}
variable "backup_retention_days" {
  type = number
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35 && floor(var.backup_retention_days) == var.backup_retention_days
    error_message = "RDS backup retention must be an explicit integer from 1 to 35 days."
  }
}
variable "log_retention_days" {
  type = number
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "Select a supported CloudWatch retention duration."
  }
}
variable "postgres_version" { type = string }
variable "postgres_family" { type = string }
variable "db_instance_class" { type = string }
variable "db_storage_gib" {
  type = number
  validation {
    condition     = var.db_storage_gib >= 20
    error_message = "Database storage must be at least 20 GiB."
  }
}
variable "db_max_storage_gib" { type = number }
variable "db_free_storage_alarm_bytes" { type = number }
variable "multi_az" {
  description = "A second-zone standby doubles the database cost (IDEA-046 B1)."
  type        = bool
  default     = false
}
variable "db_log_exports" {
  description = "PostgreSQL log types exported to CloudWatch (billed per GB ingested)."
  type        = list(string)
  default     = []
}
variable "enable_hosts" {
  type    = bool
  default = false
}
variable "ami_id" {
  type     = string
  default  = null
  nullable = true
}
variable "host_instance_types" {
  type    = map(string)
  default = { primary = "t3.small", signer = "t3.micro" }
  validation {
    condition = (toset(keys(var.host_instance_types)) == toset(["primary", "signer"])
    && alltrue([for t in values(var.host_instance_types) : can(regex("^t[34]g?\\.", t))]))
    error_message = "Give a burstable (t3/t4g) type for exactly the primary and signer hosts; standard credits apply."
  }
}
variable "allow_teardown" {
  description = "Only for the post-audit teardown: lifts database deletion and instance termination protection."
  type        = bool
  default     = false
}
variable "monthly_budget_usd" {
  description = "Monthly AWS cost budget; alerts at 50, 75 and 90 percent of actual spend."
  type        = number
  default     = 90
  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "Budget must be positive."
  }
}
variable "budget_notification_emails" {
  description = "Alert recipients. Supplied in an uncommitted tfvars file; no budget alert is created without one."
  type        = list(string)
  default     = []
  sensitive   = true
}
variable "alarm_notification_emails" {
  description = "Alarm email recipients (IDEA-047 R5). Supplied in an uncommitted tfvars file; no topic is created without one."
  type        = list(string)
  default     = []
  sensitive   = true
}
variable "enable_external_https" {
  description = "Opt-in internet gateway, public IPv4 and HTTPS egress for the primary host only; no services start."
  type        = bool
  default     = false
}
variable "enable_development_ssm" {
  type    = bool
  default = false
}
variable "alarm_topic_arns" {
  description = "Existing explicitly authorized destinations; empty creates silent alarms only."
  type        = list(string)
  default     = []
}
