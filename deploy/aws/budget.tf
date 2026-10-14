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

# The $100 credit is one-off and hosting spans several calendar months, so a monthly budget alone cannot show that
# total spend is about to use it up (the Free plan then closes the account, IDEA-046 B4). This budget runs over the
# whole credit period (IDEA-049 D-FND-016, #63); the monthly one above keeps the pace.
resource "aws_budgets_budget" "credit" {
  count             = nonsensitive(length(var.budget_notification_emails)) > 0 ? 1 : 0
  name              = "${var.name}-credit"
  budget_type       = "COST"
  time_unit         = "ANNUALLY"
  time_period_start = var.credit_period_start
  time_period_end   = var.credit_period_end
  limit_amount      = format("%.2f", var.credit_budget_usd)
  limit_unit        = "USD"
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
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_notification_emails
  }
}
