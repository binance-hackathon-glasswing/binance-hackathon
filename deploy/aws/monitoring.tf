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
  alarm_actions       = var.alarm_topic_arns
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
  alarm_actions       = var.alarm_topic_arns
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
  alarm_actions       = var.alarm_topic_arns
  dimensions          = { Deployment = var.name, Service = "archive" }
}
