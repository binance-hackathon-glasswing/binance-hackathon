# IDEA-100 DB1/DB2: database health alarms and query/lock visibility for the 1 GB burstable instance. Plan only.
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
  db_instance_class           = "db.t4g.micro"
  db_storage_gib              = 20
  db_max_storage_gib          = 100
  db_free_storage_alarm_bytes = 5000000000
  alarm_topic_arns            = ["arn:aws:sns:ap-southeast-2:123456789012:larp-fixture-existing"]
}

run "db1_five_database_alarms" {
  command = plan
  assert {
    condition     = length(aws_cloudwatch_metric_alarm.database_health) == 5
    error_message = "DB1: exactly five database health alarms."
  }
  assert {
    condition = { for k, a in aws_cloudwatch_metric_alarm.database_health : k => [a.namespace, a.metric_name, a.comparison_operator, a.threshold, a.period * a.evaluation_periods] } == {
      credit-balance  = ["AWS/RDS", "CPUCreditBalance", "LessThanThreshold", 20, 900]
      surplus-credits = ["AWS/RDS", "CPUSurplusCreditBalance", "GreaterThanThreshold", 10, 900]
      freeable-memory = ["AWS/RDS", "FreeableMemory", "LessThanThreshold", 62914560, 600]
      swap-usage      = ["AWS/RDS", "SwapUsage", "GreaterThanThreshold", 629145600, 900]
      connections     = ["AWS/RDS", "DatabaseConnections", "GreaterThanThreshold", 15, 300]
    }
    error_message = "DB1: metric, comparison, threshold or window differs from IDEA-100."
  }
  assert {
    condition     = alltrue([for a in aws_cloudwatch_metric_alarm.database_health : toset(a.alarm_actions) == toset(["arn:aws:sns:ap-southeast-2:123456789012:larp-fixture-existing"]) && a.dimensions["DBInstanceIdentifier"] == "larp-fixture" && strcontains(a.alarm_description, "F-114")])
    error_message = "DB1: every alarm notifies the alarm topics, watches this instance and carries the scored-run footer."
  }
  assert {
    condition     = [for k in sort(keys(aws_cloudwatch_metric_alarm.database_health)) : aws_cloudwatch_metric_alarm.database_health[k].treat_missing_data] == ["notBreaching", "breaching", "notBreaching", "notBreaching", "notBreaching"]
    error_message = "DB1: only the credit-balance alarm treats missing data as breaching."
  }
}

run "db2_query_and_lock_visibility" {
  command = plan
  assert {
    condition = { for p in aws_db_parameter_group.larp.parameter : p.name => p.value } == {
      "rds.force_ssl"              = "1"
      "shared_preload_libraries"   = "pg_stat_statements"
      "pg_stat_statements.track"   = "top"
      "log_min_duration_statement" = "1000"
      "log_lock_waits"             = "1"
    }
    error_message = "DB2: the parameter group keeps force_ssl and adds exactly the four IDEA-100 parameters."
  }
  assert {
    condition     = one([for p in aws_db_parameter_group.larp.parameter : p.apply_method if p.name == "shared_preload_libraries"]) == "pending-reboot"
    error_message = "DB2: the preload library applies at the next reboot, never immediately."
  }
}
