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
  # Shown in every alarm email: what fired, what the system does on its own, where to look. During the scored run
  # people only watch and record (docs/build/runbook.md preamble; F-114).
  alarm_footer = "Scored run: watch and record only, no manual action on the agent (F-114). Runbook: docs/build/runbook.md"
  # Published by larp.runtime.operations on primary every minute (Maintenance.service_health). Missing data means
  # the check itself is down, which is as bad as the failure it watches for.
  service_alarms = {
    runtime-heartbeat = {
      service     = "runtime", metric = "Heartbeat", comparison = "LessThanThreshold", threshold = 1
      description = "larp-runtime has sent no heartbeat for 10 minutes (missing data counts). systemd restarts a crash within about 10 s; exit codes 2, 3 and 4 are not restarted. Check `systemctl status larp-runtime` and its journal for the exit reason (runbook section 2)."
    }
    runtime-halted = {
      service     = "runtime", metric = "Halted", comparison = "GreaterThanThreshold", threshold = 0
      description = "The runtime is in HALT: rounds still run and are logged, new risk stops. Read the HALT reason in the latest round log; the runbook section 3 table says which reasons clear on their own."
    }
    runtime-quarantined = {
      service     = "runtime", metric = "Quarantined", comparison = "GreaterThanThreshold", threshold = 0
      description = "The journal failed verification and the run is quarantined: every write and signature is fenced, so the agent has stopped trading. It does not clear during the scored run; a restore and reviewed takeover happen only outside it (runbook section 4)."
    }
    runtime-low-gas = {
      service     = "runtime", metric = "GasPairUnaffordable", comparison = "GreaterThanThreshold", threshold = 0
      description = "Initial-only gas is below the pinned action budget, including an approve+swap pair. LOW_GAS is journaled at a quiet execution boundary. Buys preserve the exit reserve; affordable reductions and exits continue. No top-up or global HALT is triggered. Check gas_health and the measured reserve/seeding acceptance (IDEA-061 LD08)."
    }
    uploader-overdue = {
      service     = "uploader", metric = "OverdueLogs", comparison = "GreaterThanThreshold", threshold = 0
      description = "A round log has not been acknowledged by the ai-seeds receiver in time. Past the delivery deadline (next UTC midnight + 2 h) the runtime HALTs with DELIVERY_DEADLINE until nothing is overdue. Check larp-uploader and its route to the receiver (runbook section 3)."
    }
    signer-unanswered = {
      service     = "signer", metric = "UnansweredRequests", comparison = "GreaterThanThreshold", threshold = 0
      description = "Signing requests from primary are waiting with no answer from the signer host. Check larp-signer on the signer host and its route from primary (runbook section 1, step 7)."
    }
  }
}
resource "aws_cloudwatch_log_group" "host" {
  for_each          = local.hosts
  name              = "/larp/${var.name}/${each.key}"
  retention_in_days = var.log_retention_days
}
resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.name}-database-storage"
  alarm_description   = "RDS free storage has been below ${var.db_free_storage_alarm_bytes} bytes for 2 minutes (missing data counts). When the disk fills, writes fail and the runtime stops committing. Check database growth per round (IDEA-049-D R-09). ${local.alarm_footer}"
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
# IDEA-100 DB1: the 1 GB burstable database stalled on 2026-10-25 when its CPU credits ran out under a looping job.
# These watch the instance itself: credits, borrowed (surplus) credits, memory, swap and connections.
locals {
  database_alarms = {
    credit-balance = {
      metric      = "CPUCreditBalance", comparison = "LessThanThreshold", threshold = 20, periods = 3, missing = "breaching"
      description = "RDS CPU credits are below 20 for 15 minutes (missing data counts). A burstable instance out of credits falls to its 10 % CPU baseline and queries queue (IDEA-100). Check RDS CPU and the top queries (checks/db-top-queries.sh), and the archive job's last runs."
    }
    surplus-credits = {
      metric      = "CPUSurplusCreditBalance", comparison = "GreaterThanThreshold", threshold = 10, periods = 3, missing = "notBreaching"
      description = "RDS is borrowing CPU credits (surplus above 10 for 15 minutes). Unlimited mode does not throttle, but sustained surplus is charged against the account credits (IDEA-100 billing check). Check what keeps the CPU above its baseline (checks/db-top-queries.sh)."
    }
    freeable-memory = {
      metric      = "FreeableMemory", comparison = "LessThanThreshold", threshold = 62914560, periods = 2, missing = "notBreaching"
      description = "RDS freeable memory is below 60 MiB for 10 minutes. The 1 GB instance then swaps and slows every service. Check connections and the archive job (IDEA-100)."
    }
    swap-usage = {
      metric      = "SwapUsage", comparison = "GreaterThanThreshold", threshold = 629145600, periods = 3, missing = "notBreaching"
      description = "RDS swap use is above 600 MiB for 15 minutes; queries are slowed by paging (IDEA-100). Check memory, connections and the top queries."
    }
    connections = {
      metric      = "DatabaseConnections", comparison = "GreaterThanThreshold", threshold = 15, periods = 1, missing = "notBreaching"
      description = "More than 15 database connections for 5 minutes. The services normally hold a few; a climb usually means a stuck or looping client (IDEA-100). Check `systemctl` on primary and signer for restart loops."
    }
  }
}
resource "aws_cloudwatch_metric_alarm" "database_health" {
  for_each            = local.database_alarms
  alarm_name          = "${var.name}-database-${each.key}"
  alarm_description   = "${each.value.description} ${local.alarm_footer}"
  comparison_operator = each.value.comparison
  evaluation_periods  = each.value.periods
  metric_name         = each.value.metric
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = each.value.comparison == "LessThanThreshold" ? "Minimum" : "Maximum"
  threshold           = each.value.threshold
  treat_missing_data  = each.value.missing
  alarm_actions       = local.alarm_actions
  dimensions          = { DBInstanceIdentifier = aws_db_instance.larp.identifier }
}
resource "aws_cloudwatch_metric_alarm" "host" {
  for_each            = aws_instance.host
  alarm_name          = "${var.name}-${each.key}-host-status"
  alarm_description   = "EC2 status checks on ${each.key} have failed for 2 minutes (missing data counts). The auto-recover (hardware) and auto-reboot (instance) alarms act on their own and the services restart under systemd; this should clear within about 10 minutes. ${local.alarm_footer}"
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
  alarm_description   = "AWS reported a hardware fault on ${each.key}. CloudWatch is moving the instance to healthy hardware with the same disk and address; the services restart under systemd with a RESTART incident (runbook section 2). ${local.alarm_footer}"
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
  alarm_description   = "${each.key} has failed its instance status check for 3 minutes (kernel, memory or network). CloudWatch is rebooting it; the disks and address stay, and the services restart under systemd (runbook section 2, #60). ${local.alarm_footer}"
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
  alarm_description   = each.key == "Healthy" ? "The archive job reports missed or unacknowledged hourly anchors or backups (health().missed). A later acknowledged slot of the same kind supersedes a missed one. Check larp-archive.timer on primary and the Object Lock bucket (runbook section 4, IDEA-036). ${local.alarm_footer}" : "The archive job has not reported for 10 minutes (missing data counts). Check larp-archive.timer and its last run on primary (runbook section 4). ${local.alarm_footer}"
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
  alarm_description   = "${each.value.description} ${local.alarm_footer}"
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
