mock_provider "aws" {}

variables {
  account_id                  = "123456789012"
  region                      = "ap-southeast-1"
  availability_zones          = ["ap-southeast-1a", "ap-southeast-1b"]
  environment                 = "development"
  name                        = "larp-fixture"
  vpc_cidr                    = "10.80.0.0/16"
  archive_bucket_name         = "larp-synthetic-archive-fixture"
  artifact_bucket_name        = "larp-synthetic-artifact-fixture"
  archive_retention_days      = 90
  backup_retention_days       = 7
  log_retention_days          = 30
  postgres_version            = "14.24"
  postgres_family             = "postgres14"
  db_instance_class           = "db.t3.micro"
  db_storage_gib              = 20
  db_max_storage_gib          = 100
  db_free_storage_alarm_bytes = 5000000000
}

run "safe_defaults" {
  command = plan
  assert {
    condition     = !aws_db_instance.larp.publicly_accessible && aws_db_instance.larp.storage_encrypted && aws_db_instance.larp.deletion_protection
    error_message = "The database must be private, encrypted and deletion-protected."
  }
  assert {
    condition     = aws_db_instance.larp.manage_master_user_password && aws_db_instance.larp.iam_database_authentication_enabled
    error_message = "No database password may enter configuration/state."
  }
  assert {
    condition     = aws_s3_bucket_object_lock_configuration.archive.rule[0].default_retention[0].mode == "COMPLIANCE"
    error_message = "Archive retention must be enforced by Object Lock."
  }
  assert {
    condition     = length(aws_instance.host) == 0 && length(aws_nat_gateway.optional) == 0 && !output.signing_enabled
    error_message = "Host startup, internet access and signing must be opt-in or blocked."
  }
  assert {
    condition     = length(aws_secretsmanager_secret.service) == 3 && length(aws_iam_role.host) == 6
    error_message = "Service credentials/identities must remain separated."
  }
}
run "host_isolation" {
  command = plan
  variables {
    enable_hosts = true
    ami_id       = "ami-0123456789abcdef0"
  }
  assert {
    condition = alltrue([for host in aws_instance.host :
      !host.associate_public_ip_address && host.metadata_options[0].http_tokens == "required" && host.root_block_device[0].encrypted
    ])
    error_message = "All hosts must have private addresses, encrypted disks and IMDSv2."
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.external_https) == 0
    error_message = "No external egress by default."
  }
}
run "reject_final_interactive_access" {
  command = plan
  variables {
    environment            = "final"
    enable_development_ssm = true
  }
  expect_failures = [aws_iam_role_policy_attachment.development_ssm]
}

run "archive_retention_reaches_end_of_2026" {
  command = plan
  variables {
    archive_retention_days = 81
  }
  expect_failures = [var.archive_retention_days]
}
