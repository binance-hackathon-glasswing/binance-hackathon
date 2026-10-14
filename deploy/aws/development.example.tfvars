# IDEA-046 lean development stack. Copy to development.tfvars (ignored by Git) and fill the placeholders.
# Never commit the copy: it holds the account ID and alert email.
account_id         = "<12-digit account ID>"
region             = "ap-southeast-2" # IDEA-046 B3: Sydney for now; revisit before final activation (Oct 27)
availability_zones = ["ap-southeast-2a", "ap-southeast-2b"]
environment        = "development"
name               = "larp-dev"
vpc_cidr           = "10.80.0.0/16"

# Globally unique bucket names.
archive_bucket_name  = "<unique>-larp-dev-archive"
artifact_bucket_name = "<unique>-larp-dev-artifacts"

# 82 days is the floor (covers all of 2026-12-31). COMPLIANCE retention can never be shortened once objects exist.
archive_retention_days = 82
backup_retention_days  = 1 # the AWS Free plan refuses longer automated RDS backups (IDEA-046, 2026-10-14)
log_retention_days     = 14

# Matches the PostgreSQL version CI tests (14.24 is available on db.t4g.micro in Sydney, checked 2026-10-12).
postgres_version            = "14.24"
postgres_family             = "postgres14"
db_instance_class           = "db.t4g.micro"
db_storage_gib              = 20
db_max_storage_gib          = 30
db_free_storage_alarm_bytes = 4000000000

# Costed Option B defaults: single-zone database, t3.small + t3.micro, standard CPU credits.
# Hosts and internet egress stay off until an image exists and a rehearsal needs them.
enable_hosts          = false
enable_external_https = false

monthly_budget_usd         = 90
budget_notification_emails = ["<your email>"]
# Alarm emails (each address confirms an SNS subscription). Optional; alarms stay silent without one.
alarm_notification_emails = ["<your email>"]
