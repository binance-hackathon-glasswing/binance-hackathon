# IDEA-092: the private dashboard's own stack, separate from deploy/aws (its own state; outside the release files).
terraform {
  required_version = "= 1.13.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.61.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = { Project = "LARP", Environment = var.environment, ManagedBy = "Terraform", Purpose = "IDEA-092 dashboard" }
  }
}
