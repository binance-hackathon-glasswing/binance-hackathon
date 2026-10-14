locals {
  # IDEA-046 B1: two hosts. `primary` runs the coordinator, execution service, evidence worker, uploader and
  # archive maintenance; `signer` holds only the wallet key and never has an internet route.
  hosts    = toset(["primary", "signer"])
  db_hosts = toset(["primary", "signer"])
  external = var.enable_external_https ? toset(["primary"]) : toset([])
}
resource "aws_vpc" "larp" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}
# Private subnets in two zones: the database subnet group needs two; the signer uses the first.
resource "aws_subnet" "private" {
  count                   = 2
  vpc_id                  = aws_vpc.larp.id
  availability_zone       = var.availability_zones[count.index]
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  map_public_ip_on_launch = false
}
resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.larp.id
}
resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
# The primary host's subnet. It has an internet route only when external HTTPS is enabled; there is no NAT
# gateway (IDEA-046: ≈ $43/month each), so private hosts never reach the internet.
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.larp.id
  availability_zone       = var.availability_zones[0]
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 2)
  map_public_ip_on_launch = false
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.larp.id
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
resource "aws_internet_gateway" "optional" {
  count  = var.enable_external_https ? 1 : 0
  vpc_id = aws_vpc.larp.id
}
resource "aws_route" "internet" {
  count                  = var.enable_external_https ? 1 : 0
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.optional[0].id
}
resource "aws_security_group" "host" {
  for_each    = local.hosts
  name_prefix = "${var.name}-${each.key}-"
  vpc_id      = aws_vpc.larp.id
  description = "No inbound access; explicit service egress only"
}
resource "aws_security_group" "database" {
  name_prefix = "${var.name}-db-"
  vpc_id      = aws_vpc.larp.id
}
resource "aws_vpc_security_group_ingress_rule" "database" {
  for_each                     = local.db_hosts
  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = aws_security_group.host[each.key].id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
resource "aws_vpc_security_group_egress_rule" "database" {
  for_each                     = local.db_hosts
  security_group_id            = aws_security_group.host[each.key].id
  referenced_security_group_id = aws_security_group.database.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
# Free gateway endpoint: release artifacts and the archive reach S3 without the internet.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.larp.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat(aws_route_table.private[*].id, [aws_route_table.public.id])
}
resource "aws_vpc_security_group_egress_rule" "s3" {
  for_each          = local.hosts
  security_group_id = aws_security_group.host[each.key].id
  prefix_list_id    = aws_vpc_endpoint.s3.prefix_list_id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
# Binance, model, filing sources and AWS APIs (Secrets Manager, CloudWatch, SSM) over public endpoints.
resource "aws_vpc_security_group_egress_rule" "external_https" {
  for_each          = local.external
  security_group_id = aws_security_group.host[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
