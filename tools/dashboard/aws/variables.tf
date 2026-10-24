variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Select the target AWS account explicitly."
  }
}
variable "region" { type = string }
variable "environment" {
  type = string
  validation {
    condition     = contains(["development", "rehearsal", "final"], var.environment)
    error_message = "Use the environment of the run the dashboard watches."
  }
}
variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.name))
    error_message = "Use a short lowercase resource prefix."
  }
}
variable "bucket_name" { type = string }
variable "primary_instance_id" {
  type        = string
  description = "The run's primary host: the only instance the two read-only SSM documents may run on."
  validation {
    condition     = can(regex("^i-[0-9a-f]{8,17}$", var.primary_instance_id))
    error_message = "Give the primary's EC2 instance ID."
  }
}
variable "wallet" {
  type        = string
  description = "The wallet the chain monitor watches (the final wallet for the scored run)."
  validation {
    condition     = can(regex("^0x[0-9a-fA-F]{40}$", var.wallet))
    error_message = "Give the wallet's 0x address."
  }
}
variable "start_nonce" {
  type        = number
  description = "The wallet's nonce at the run's start (its first agent transaction)."
  validation {
    condition     = var.start_nonce >= 0 && floor(var.start_nonce) == var.start_nonce
    error_message = "The start nonce is a whole number."
  }
}
variable "start_usdt" {
  type        = number
  description = "Opening equity in USDT, excluding BNB, against which the page measures return."
  validation {
    condition     = var.start_usdt > 0
    error_message = "The opening equity must be positive."
  }
}
variable "web3_secret_arn" {
  type        = string
  default     = null
  description = "Optional Secrets Manager secret with the read-only Web3 key (prices for equity and drawdown)."
}
variable "package_path" {
  type        = string
  description = "The Lambda package from `python -m tools.dashboard.aws.package --out <zip>`."
}
variable "log_retention_days" {
  type = number
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90], var.log_retention_days)
    error_message = "Select a supported CloudWatch retention duration up to 90 days."
  }
}
