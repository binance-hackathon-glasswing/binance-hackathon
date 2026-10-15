# IDEA-047 R5: alarms notify an optional email topic (recipients from an uncommitted tfvars file; each address must
# confirm its subscription) plus any existing topics passed in alarm_topic_arns.
resource "aws_sns_topic" "alarms" {
  count = nonsensitive(length(var.alarm_notification_emails)) > 0 ? 1 : 0
  name  = "${var.name}-alarms"
}
resource "aws_sns_topic_subscription" "alarm_email" {
  count     = nonsensitive(length(var.alarm_notification_emails))
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_notification_emails[count.index]
}
locals {
  alarm_actions = concat(aws_sns_topic.alarms[*].arn, var.alarm_topic_arns)
  # Published by larp.runtime.operations on primary every minute (Maintenance.service_health). Missing data means
  # the check itself is down, which is as bad as the failure it watches for.
  service_alarms = {
    runtime-heartbeat   = { service = "runtime", metric = "Heartbeat", comparison = "LessThanThreshold", threshold = 1 }
    runtime-halted      = { service = "runtime", metric = "Halted", comparison = "GreaterThanThreshold", threshold = 0 }
    runtime-quarantined = { service = "runtime", metric = "Quarantined", comparison = "GreaterThanThreshold", threshold = 0 }
    uploader-overdue    = { service = "uploader", metric = "OverdueLogs", comparison = "GreaterThanThreshold", threshold = 0 }
    signer-unanswered   = { service = "signer", metric = "UnansweredRequests", comparison = "GreaterThanThreshold", threshold = 0 }
  }
}
resource "aws_cloudwatch_log_group" "host" {
  for_each          = local.hosts
  name              = "/larp/${var.name}/${each.key}"
  retention_in_days = var.log_retention_days
}
resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.name}-database-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Minimum"
  threshold           = var.db_free_storage_alarm_bytes
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  dimensions          = { DBInstanceIdentifier = aws_db_instance.larp.identifier }
}
resource "aws_cloudwatch_metric_alarm" "host" {
  for_each            = aws_instance.host
  alarm_name          = "${var.name}-${each.key}-host-status"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  dimensions          = { InstanceId = each.value.id }
}
# Moves the instance to healthy hardware with the same disk and address when AWS reports a host fault; the
# services restart under systemd without a human action (F-114). Missing data never triggers a recovery.
resource "aws_cloudwatch_metric_alarm" "recover" {
  for_each            = aws_instance.host
  alarm_name          = "${var.name}-${each.key}-auto-recover"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed_System"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = concat(["arn:aws:automate:${var.region}:ec2:recover"], local.alarm_actions)
  dimensions          = { InstanceId = each.value.id }
}
# An instance-status failure (kernel panic, memory exhaustion, broken network configuration) is not a hardware fault,
# so `recover` does not act on it. A reboot keeps the instance, its disks and its address; the services start again
# under systemd with no person acting (F-114; IDEA-049 D-FND-017, #60).
resource "aws_cloudwatch_metric_alarm" "reboot" {
  for_each            = aws_instance.host
  alarm_name          = "${var.name}-${each.key}-auto-reboot"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "StatusCheckFailed_Instance"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = concat(["arn:aws:automate:${var.region}:ec2:reboot"], local.alarm_actions)
  dimensions          = { InstanceId = each.value.id }
}
resource "aws_cloudwatch_metric_alarm" "maintenance" {
  for_each            = toset(["Healthy", "Heartbeat"])
  alarm_name          = "${var.name}-archive-${lower(each.key)}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = each.key
  namespace           = "LARP/Runtime"
  period              = 300
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  dimensions          = { Deployment = var.name, Service = "archive" }
}
# Service-level alarms exist only while hosts run: with hosts off every one would sit in ALARM on missing data.
resource "aws_cloudwatch_metric_alarm" "service" {
  for_each            = var.enable_hosts ? local.service_alarms : {}
  alarm_name          = "${var.name}-${each.key}"
  comparison_operator = each.value.comparison
  evaluation_periods  = 2
  metric_name         = each.value.metric
  namespace           = "LARP/Runtime"
  period              = 300
  statistic           = each.value.comparison == "LessThanThreshold" ? "Minimum" : "Maximum"
  threshold           = each.value.threshold
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  dimensions          = { Deployment = var.name, Service = each.value.service }
}
