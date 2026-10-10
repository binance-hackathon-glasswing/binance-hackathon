locals {
  hosts    = toset(["primary", "standby", "archive", "uploader", "evidence", "signer"])
  db_hosts = toset(["primary", "standby", "archive", "uploader", "signer"])
  external = var.enable_external_https ? toset(["uploader", "evidence"]) : toset([])
}
resource "aws_vpc" "larp" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}
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
resource "aws_security_group" "endpoint" {
  name_prefix = "${var.name}-endpoints-"
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
resource "aws_vpc_security_group_ingress_rule" "endpoint" {
  for_each                     = local.hosts
  security_group_id            = aws_security_group.endpoint.id
  referenced_security_group_id = aws_security_group.host[each.key].id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}
resource "aws_vpc_security_group_egress_rule" "endpoint" {
  for_each                     = local.hosts
  security_group_id            = aws_security_group.host[each.key].id
  referenced_security_group_id = aws_security_group.endpoint.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}
resource "aws_vpc_endpoint" "services" {
  for_each            = toset(["secretsmanager", "logs", "monitoring", "ssm", "ssmmessages"])
  vpc_id              = aws_vpc.larp.id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoint.id]
}
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.larp.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id
}
resource "aws_vpc_security_group_egress_rule" "s3" {
  for_each          = local.hosts
  security_group_id = aws_security_group.host[each.key].id
  prefix_list_id    = aws_vpc_endpoint.s3.prefix_list_id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
resource "aws_internet_gateway" "optional" {
  count  = var.enable_external_https ? 1 : 0
  vpc_id = aws_vpc.larp.id
}
resource "aws_subnet" "public" {
  count             = var.enable_external_https ? 2 : 0
  vpc_id            = aws_vpc.larp.id
  availability_zone = var.availability_zones[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 2)
}
resource "aws_eip" "nat" {
  count  = var.enable_external_https ? 2 : 0
  domain = "vpc"
}
resource "aws_nat_gateway" "optional" {
  count         = var.enable_external_https ? 2 : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.optional]
}
resource "aws_route_table" "public" {
  count  = var.enable_external_https ? 1 : 0
  vpc_id = aws_vpc.larp.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.optional[0].id
  }
}
resource "aws_route_table_association" "public" {
  count          = var.enable_external_https ? 2 : 0
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}
resource "aws_route" "nat" {
  count                  = var.enable_external_https ? 2 : 0
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.optional[count.index].id
}
resource "aws_vpc_security_group_egress_rule" "external_https" {
  for_each          = local.external
  security_group_id = aws_security_group.host[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
