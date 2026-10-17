# IDEA-080 SA3/SA8 need the endpoints' subnet and security-group IDs at plan time, so this file's mock provider
# generates computed values during plan (override_during), with well-formed values where the provider validates them.
# Plan only: no apply, so no teardown of the protected storage resources.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_kms_key" {
    defaults = { arn = "arn:aws:kms:ap-southeast-2:123456789012:key/00000000-0000-0000-0000-000000000000" }
  }
  mock_resource "aws_db_instance" {
    defaults = { master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:rds-fixture", kms_key_id = "", secret_status = "active" }] }
  }
}

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

run "signer_access_is_narrow" {
  command = plan
  # Distinct IDs, so the assertions can tell the endpoint group, each host group and the subnets apart.
  override_resource {
    override_during = plan
    target          = aws_security_group.host["primary"]
    values          = { id = "sg-primary0000000001" }
  }
  override_resource {
    override_during = plan
    target          = aws_security_group.host["signer"]
    values          = { id = "sg-signer00000000002" }
  }
  override_resource {
    override_during = plan
    target          = aws_security_group.signer_endpoints[0]
    values          = { id = "sg-endpoints00000003" }
  }
  override_resource {
    override_during = plan
    target          = aws_subnet.private[0]
    values          = { id = "subnet-private000000a" }
  }
  override_resource {
    override_during = plan
    target          = aws_subnet.private[1]
    values          = { id = "subnet-private000000b" }
  }
  variables {
    enable_hosts               = true
    enable_external_https      = true
    enable_development_ssm     = true
    enable_signer_provisioning = true
    ami_id                     = "ami-0123456789abcdef0"
  }
  assert {
    condition = toset(keys(aws_vpc_endpoint.signer_ssm)) == toset(["ssm", "ssmmessages", "ec2messages"]) && alltrue([
      for e in values(aws_vpc_endpoint.signer_ssm) : e.vpc_endpoint_type == "Interface" && e.private_dns_enabled
      && e.subnet_ids == toset([aws_subnet.private[0].id])
      && e.security_group_ids == toset([aws_security_group.signer_endpoints[0].id])
    ])
    error_message = "IDEA-080 SA3: three interface endpoints with private DNS, only in the signer's private subnet."
  }
  assert {
    condition = toset(keys(aws_vpc_security_group_ingress_rule.signer_endpoints)) == toset(["primary", "signer"]) && alltrue([
      for k, r in aws_vpc_security_group_ingress_rule.signer_endpoints : r.from_port == 443 && r.to_port == 443
      && r.ip_protocol == "tcp" && r.referenced_security_group_id == aws_security_group.host[k].id
      && r.security_group_id == aws_security_group.signer_endpoints[0].id
    ])
    error_message = "IDEA-080 SA3 (corrected): the endpoints admit HTTPS from the two host groups only; private DNS is VPC-wide."
  }
  assert {
    condition = (length(aws_vpc_security_group_egress_rule.signer_endpoints) == 1
      && aws_vpc_security_group_egress_rule.signer_endpoints[0].security_group_id == aws_security_group.host["signer"].id
      && aws_vpc_security_group_egress_rule.signer_endpoints[0].referenced_security_group_id == aws_security_group.signer_endpoints[0].id
    && aws_vpc_security_group_egress_rule.signer_endpoints[0].from_port == 443)
    error_message = "IDEA-080 SA8: the signer's only extra egress is HTTPS to the endpoint group."
  }
  assert {
    condition     = keys(aws_vpc_security_group_egress_rule.external_https) == ["primary"] && !aws_instance.host["signer"].associate_public_ip_address
    error_message = "IDEA-080 SA4: the signer still has no internet egress and no public address."
  }
  assert {
    condition     = length(aws_iam_role_policy_attachment.signer_ssm) == 1 && aws_iam_role_policy_attachment.signer_ssm[0].role == aws_iam_role.host["signer"].name
    error_message = "The signer gets the SSM managed-instance policy only while provisioning access is on."
  }
}
