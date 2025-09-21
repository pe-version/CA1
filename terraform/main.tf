provider "aws" {
  region = var.region
}

# Simple VPC setup
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "metals-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = { Name = "metals-igw" }
}

resource "aws_subnet" "main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "metals-subnet" }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "metals-rt" }
}

resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}

# Security Group
resource "aws_security_group" "allow_all" {
  name   = "metals-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 27017
    to_port     = 27017
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "metals-security-group" }
}

# 4 VMs
resource "aws_instance" "kafka_vm" {
  ami                    = "ami-001209a78b30e703c"
  instance_type          = "t3.small"
  key_name              = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.allow_all.id]
  subnet_id             = aws_subnet.main.id
  tags = { Name = "kafka-vm", Role = "kafka" }
}

resource "aws_instance" "mongodb_vm" {
  ami                    = "ami-001209a78b30e703c"
  instance_type          = "t3.small"
  key_name              = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.allow_all.id]
  subnet_id             = aws_subnet.main.id
  tags = { Name = "mongodb-vm", Role = "database" }
}

resource "aws_instance" "processor_vm" {
  ami                    = "ami-001209a78b30e703c"
  instance_type          = "t3.small"
  key_name              = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.allow_all.id]
  subnet_id             = aws_subnet.main.id
  tags = { Name = "processor-vm", Role = "processor" }
}

resource "aws_instance" "producer_vm" {
  ami                    = "ami-001209a78b30e703c"
  instance_type          = "t3.small"
  key_name              = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.allow_all.id]
  subnet_id             = aws_subnet.main.id
  tags = { Name = "producer-vm", Role = "producer" }
}