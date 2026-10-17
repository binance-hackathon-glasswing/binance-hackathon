# IDEA-080: temporary access to the isolated signer for provisioning and key placement. Off by default (SA1).
# While on, three SSM interface endpoints sit in the signer's private subnet. The signer still has no internet
# route; it reaches only these endpoints, the database and the S3 gateway. Set the variable back to false and apply
# once the bundle, signer.json and key are in place (SA5), and never during the scored run (SA7, F-114).
locals {
  signer_access     = var.enable_signer_provisioning
  signer_ssm_points = local.signer_access ? toset(["ssm", "ssmmessages", "ec2messages"]) : toset([])
}
resource "aws_security_group" "signer_endpoints" {
  count       = local.signer_access ? 1 : 0
  name_prefix = "${var.name}-signer-endpoints-"
  vpc_id      = aws_vpc.larp.id
  description = "IDEA-080: temporary SSM endpoints for signer provisioning; HTTPS from the two hosts only"
  lifecycle {
    precondition {
      condition     = var.environment == "development"
      error_message = "IDEA-080 SA2: signer provisioning access is permitted by this template only in development."
    }
  }
}
# SA3 (as corrected, PR #143): private DNS is VPC-wide, so primary's SSM traffic also lands on these endpoints while
# they exist. Both host groups are admitted, and nothing else.
resource "aws_vpc_security_group_ingress_rule" "signer_endpoints" {
  for_each                     = local.signer_access ? local.hosts : toset([])
  security_group_id            = aws_security_group.signer_endpoints[0].id
  referenced_security_group_id = aws_security_group.host[each.key].id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}
# SA8: the signer's only extra egress is HTTPS to the endpoint group, removed with it.
resource "aws_vpc_security_group_egress_rule" "signer_endpoints" {
  count                        = local.signer_access ? 1 : 0
  security_group_id            = aws_security_group.host["signer"].id
  referenced_security_group_id = aws_security_group.signer_endpoints[0].id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}
resource "aws_vpc_endpoint" "signer_ssm" {
  for_each            = local.signer_ssm_points
  vpc_id              = aws_vpc.larp.id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private[0].id]
  security_group_ids  = [aws_security_group.signer_endpoints[0].id]
  private_dns_enabled = true
  tags                = { Name = "${var.name}-signer-${each.key}", Purpose = "IDEA-080 temporary signer provisioning" }
}
resource "aws_iam_role_policy_attachment" "signer_ssm" {
  count      = local.signer_access ? 1 : 0
  role       = aws_iam_role.host["signer"].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  lifecycle {
    precondition {
      condition     = var.environment == "development"
      error_message = "IDEA-080 SA2: signer provisioning access is permitted by this template only in development."
    }
  }
}
