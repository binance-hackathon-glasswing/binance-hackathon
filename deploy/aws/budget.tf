# IDEA-046 B4/L06: actual-spend alerts against the credit budget. Recipients come from an uncommitted tfvars file.
resource "aws_budgets_budget" "monthly" {
  count        = nonsensitive(length(var.budget_notification_emails)) > 0 ? 1 : 0
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  time_unit    = "MONTHLY"
  limit_amount = format("%.2f", var.monthly_budget_usd)
  limit_unit   = "USD"
  # Promotional credits pay the bill but still consume the shared credit balance.
  cost_types {
    include_credit = false
  }
  dynamic "notification" {
    for_each = toset([50, 75, 90])
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.budget_notification_emails
    }
  }
}
