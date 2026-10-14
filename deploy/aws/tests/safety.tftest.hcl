mock_provider "aws" {}

variables {
  account_id                  = "123456789012"
  region                      = "ap-southeast-2"
  availability_zones          = ["ap-southeast-2a", "ap-southeast-2b"]
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
    condition     = length(aws_instance.host) == 0 && length(aws_internet_gateway.optional) == 0 && length(aws_route.internet) == 0 && !output.signing_enabled
    error_message = "Host startup, internet access and signing must be opt-in or blocked."
  }
  assert {
    condition     = length(aws_secretsmanager_secret.service) == 3 && length(aws_iam_role.host) == 2
    error_message = "IDEA-046: two host identities and three managed secrets; the wallet key is not a managed secret."
  }
  assert {
    condition     = !aws_db_instance.larp.multi_az && length(aws_db_instance.larp.enabled_cloudwatch_logs_exports) == 0
    error_message = "Lean defaults: single-zone database and no billed log export."
  }
  assert {
    condition     = aws_vpc_endpoint.s3.vpc_endpoint_type == "Gateway" && length(aws_budgets_budget.monthly) == 0
    error_message = "Only the free S3 gateway endpoint; no budget without a recipient."
  }
  assert {
    condition     = !aws_s3_bucket.artifacts.force_destroy && !aws_s3_bucket.archive.force_destroy
    error_message = "Buckets are never force-destroyed outside a teardown."
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
      && host.credit_specification[0].cpu_credits == "standard" && host.disable_api_termination
    ])
    error_message = "Hosts: no public address by default, IMDSv2, encrypted disks, standard CPU credits, termination protection."
  }
  assert {
    condition     = aws_instance.host["primary"].instance_type == "t3.small" && aws_instance.host["signer"].instance_type == "t3.micro"
    error_message = "Default instance sizes are the costed Option B sizes."
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.external_https) == 0
    error_message = "No external egress by default."
  }
  assert {
    condition     = length(aws_cloudwatch_metric_alarm.recover) == 2
    error_message = "Each host recovers automatically from an AWS hardware fault."
  }
}
run "internet_reaches_primary_only" {
  command = plan
  variables {
    enable_hosts          = true
    enable_external_https = true
    ami_id                = "ami-0123456789abcdef0"
  }
  assert {
    condition     = aws_instance.host["primary"].associate_public_ip_address && !aws_instance.host["signer"].associate_public_ip_address
    error_message = "Only the primary host gets a public address."
  }
  assert {
    condition     = keys(aws_vpc_security_group_egress_rule.external_https) == ["primary"] && length(aws_route.internet) == 1
    error_message = "Internet egress exists only for the primary host."
  }
  assert {
    condition     = !contains(flatten(values(local.secret_readers)), "signer")
    error_message = "The signer reads no managed secret (wallet key is a root-only file, IDEA-046 B2)."
  }
}
run "runtime_secret_exists" {
  command = plan
  assert {
    condition     = aws_secretsmanager_secret.service["runtime"].name == "larp-fixture/runtime"
    error_message = "The runtime host's secret (wallet address and market-data keys) must exist; values stay outside Terraform."
  }
}
run "host_database_users_match_sql_roles" {
  command = plan
  assert {
    condition = local.db_users == {
      primary = ["larp_runtime", "larp_execution", "larp_archive", "larp_uploader"]
      signer  = ["larp_signer"]
    }
    error_message = "IAM database login resources must use provisioned service roles, not host names."
  }
  assert {
    condition     = toset(keys(local.db_users)) == local.db_hosts
    error_message = "Exactly the database hosts receive database logins."
  }
  assert {
    # Every role deploy/postgres/roles.sql grants rds_iam must be reachable from some host.
    condition = toset(flatten(values(local.db_users))) == toset(
    ["larp_archive", "larp_uploader", "larp_runtime", "larp_execution", "larp_signer"])
    error_message = "Each IAM-authenticated SQL role needs a host that may request its token."
  }
}
run "budget_alerts_with_recipient" {
  command = plan
  variables {
    budget_notification_emails = ["alerts@fixture.invalid"]
  }
  assert {
    condition     = length(aws_budgets_budget.monthly) == 1 && aws_budgets_budget.monthly[0].limit_amount == "90.00" && length(aws_budgets_budget.monthly[0].notification) == 3
    error_message = "A monthly budget alerts at 50, 75 and 90 percent of actual spend."
  }
}
run "teardown_lifts_only_operational_protection" {
  command = plan
  variables {
    enable_hosts   = true
    ami_id         = "ami-0123456789abcdef0"
    allow_teardown = true
  }
  assert {
    condition     = !aws_db_instance.larp.deletion_protection && aws_s3_bucket.artifacts.force_destroy && alltrue([for host in aws_instance.host : !host.disable_api_termination])
    error_message = "Teardown lifts database, instance and artifact protection."
  }
  assert {
    condition     = !aws_s3_bucket.archive.force_destroy && aws_s3_bucket_object_lock_configuration.archive.rule[0].default_retention[0].mode == "COMPLIANCE"
    error_message = "The write-once archive is never force-destroyed."
  }
}
run "non_burstable_types_are_refused" {
  command = plan
  variables {
    host_instance_types = { primary = "m5.large", signer = "t3.micro" }
  }
  expect_failures = [var.host_instance_types]
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
run "service_alarms_follow_the_hosts" {
  command = plan
  variables {
    enable_hosts = true
    ami_id       = "ami-0123456789abcdef0"
  }
  assert {
    condition = toset(keys(aws_cloudwatch_metric_alarm.service)) == toset(
    ["runtime-heartbeat", "runtime-halted", "runtime-quarantined", "uploader-overdue", "signer-unanswered"])
    error_message = "IDEA-047 R5: one alarm per service signal while hosts run."
  }
  assert {
    condition     = alltrue([for a in aws_cloudwatch_metric_alarm.service : a.treat_missing_data == "breaching" && a.namespace == "LARP/Runtime"])
    error_message = "A silent check must alarm like the failure it watches for."
  }
  assert {
    condition     = aws_cloudwatch_metric_alarm.service["runtime-heartbeat"].comparison_operator == "LessThanThreshold" && aws_cloudwatch_metric_alarm.service["signer-unanswered"].threshold == 0
    error_message = "Heartbeat alarms below 1; counts alarm above 0."
  }
  assert {
    condition     = length(aws_sns_topic.alarms) == 0 && length(aws_sns_topic_subscription.alarm_email) == 0
    error_message = "No alarm topic without recipients."
  }
}
run "alarm_emails_create_one_topic" {
  command = plan
  variables {
    enable_hosts              = true
    ami_id                    = "ami-0123456789abcdef0"
    alarm_notification_emails = ["ops@fixture.invalid", "backup@fixture.invalid"]
  }
  assert {
    condition     = length(aws_sns_topic.alarms) == 1 && length(aws_sns_topic_subscription.alarm_email) == 2
    error_message = "One topic and one email subscription per address."
  }
}
run "service_alarms_off_without_hosts" {
  command = plan
  assert {
    condition     = length(aws_cloudwatch_metric_alarm.service) == 0
    error_message = "With hosts off the service alarms would sit in ALARM on missing data."
  }
}
