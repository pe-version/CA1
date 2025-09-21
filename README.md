# CA1 - Metals Pipeline Infrastructure as Code

**Student:** Philip Eykamp  
**Course:** CS 5287  
**Project:** Infrastructure as Code (IaC) Implementation

## Overview

This project transforms a manual metals price processing pipeline into a fully automated Infrastructure as Code (IaC) deployment using Terraform and Ansible. The system processes real-time metals pricing data through a distributed pipeline running on AWS.

## Architecture

### Infrastructure
- **4 AWS EC2 Instances** (t3.small)
  - Kafka VM: Apache Kafka + Zookeeper for message streaming
  - MongoDB VM: Document database for processed data storage
  - Processor VM: Python application that consumes from Kafka and writes to MongoDB
  - Producer VM: Python application that fetches metals prices and publishes to Kafka

### Networking
- Custom VPC with public subnet
- Security groups configured for service communication
- Private IP networking between services
- Public access for health monitoring

### Security
- MongoDB credentials stored in AWS Secrets Manager
- SSH key-based authentication for VM access
- Restricted security group rules for internal communication

## Quick Start

### Prerequisites
- AWS CLI configured with valid credentials
- SSH key pair created in AWS EC2
- Terraform and Ansible installed locally
- Python 3.x for local development

### Deploy Everything
```bash
# Clone and navigate to project
cd ca1-metals/

# Deploy complete infrastructure and applications
./deploy.sh
```

### Verify Deployment
```bash
# Check health endpoints
curl http://PRODUCER_IP:8000/health
curl http://PROCESSOR_IP:8001/health

# Run comprehensive test
bash scripts/quick-test.sh
```

### Clean Up
```bash
# Destroy all AWS resources
./destroy.sh
```

## Manual Deployment

### Infrastructure Provisioning
```bash
cd terraform/

# Configure your SSH key
echo 'ssh_key_name = "your-key-name"' > terraform.tfvars

# Deploy infrastructure
terraform init
terraform plan
terraform apply

# Get outputs for next step
terraform output
```

### Application Deployment
```bash
cd ansible/

# Update inventory with your IPs and SSH key path
# Edit ansible/inventory/hosts.yml

# Deploy all applications
ansible-playbook -i inventory/hosts.yml quickdeploy.yml
```

## Project Structure

```
ca1-metals/
├── deploy.sh                 # Main deployment script
├── destroy.sh               # Cleanup script
├── README.md                # This file
├── terraform/               # Infrastructure as Code
│   ├── main.tf             # AWS resources definition
│   ├── variables.tf        # Input variables
│   ├── outputs.tf          # Output values
│   └── terraform.tfvars    # Your configuration
├── ansible/                 # Configuration management
│   ├── quickdeploy.yml     # Main playbook
│   ├── inventory/
│   │   └── hosts.yml       # VM inventory
│   ├── group_vars/
│   │   └── all.yml         # Global variables
│   ├── producer/           # Producer application code
│   └── processor/          # Processor application code
└── scripts/
    └── quick-test.sh       # Pipeline validation
```

## Data Flow

1. **Producer** fetches metals pricing data and publishes to Kafka topic `metals-prices`
2. **Kafka** streams messages between producer and processor
3. **Processor** consumes messages, processes data, and stores in MongoDB
4. **MongoDB** persists processed pricing data for analysis

## Health Monitoring

### Health Endpoints
- Producer: `http://PRODUCER_IP:8000/health`
- Processor: `http://PROCESSOR_IP:8001/health`

### Health Response Format
```json
{
  "kafka_connected": true,
  "mongodb_status": "connected",
  "status": "healthy",
  "timestamp": "2025-09-20T04:02:30.019143"
}
```

## Configuration

### Terraform Variables
Update `terraform/terraform.tfvars`:
```hcl
ssh_key_name = "your-aws-key-name"
region = "us-east-2"
```

### Ansible Inventory
Update `ansible/inventory/hosts.yml` with:
- Your actual VM IP addresses
- Path to your SSH private key
- Any custom configuration

### Environment Variables
Applications support these environment variables:
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka connection string
- `MONGODB_URI`: MongoDB connection string
- `LOG_LEVEL`: Logging verbosity
- `FETCH_INTERVAL`: Producer data fetch frequency

## Secrets Management

MongoDB credentials are stored in AWS Secrets Manager:
```bash
# View current secret
aws secretsmanager get-secret-value --secret-id "metals-mongodb-password"

# Update secret
aws secretsmanager update-secret --secret-id "metals-mongodb-password" --secret-string "new-password"
```

## Troubleshooting

### Common Issues

**SSH Permission Denied**
```bash
# Fix SSH key permissions
chmod 400 ~/.ssh/your-key.pem

# Update inventory with correct key path
```

**Kafka Connection Issues**
```bash
# Check Kafka status
ansible -i inventory/hosts.yml kafka -m shell -a "docker ps"
ansible -i inventory/hosts.yml kafka -m shell -a "docker logs kafka"

# Restart Kafka containers
ansible -i inventory/hosts.yml kafka -m shell -a "docker restart kafka zookeeper"
```

**Application Not Connecting**
```bash
# Check application logs
ansible -i inventory/hosts.yml producer -m shell -a "docker logs metals-producer"
ansible -i inventory/hosts.yml processor -m shell -a "docker logs metals-processor"

# Restart applications
ansible -i inventory/hosts.yml all -m shell -a "docker restart \$(docker ps -q)"
```

### Debug Commands
```bash
# Check all container status
ansible -i inventory/hosts.yml all -m shell -a "docker ps"

# Test inter-VM connectivity
ansible -i inventory/hosts.yml processor -m shell -a "nc -zv KAFKA_PRIVATE_IP 9092"

# Check MongoDB data
ssh ubuntu@MONGODB_IP "docker exec mongodb mongosh -u admin -p password --authenticationDatabase admin metals --eval 'db.prices.countDocuments({})'"
```

## Development

### Local Testing
Applications can be tested locally with Docker:
```bash
# Start local Kafka and MongoDB
docker-compose up -d kafka mongodb

# Run applications locally
cd producer && python producer.py
cd processor && python processor.py
```

### Code Structure
- **Producer**: Fetches metals pricing data and publishes to Kafka
- **Processor**: Consumes Kafka messages and stores processed data
- **Health Checks**: Both applications expose `/health` endpoints
- **Dockerized**: Each application includes Dockerfile for containerization

## Performance

### Resource Usage
- **t3.small instances**: 2 vCPU, 2 GB RAM each
- **Storage**: 8 GB root volumes per instance
- **Network**: VPC with internet gateway for external access

### Scaling Considerations
- Kafka topic configured with 3 partitions for horizontal scaling
- MongoDB configured for single-node deployment (development)
- Applications designed for stateless horizontal scaling

## Deployment Strategy

### Idempotency
- Terraform ensures consistent infrastructure state
- Ansible tasks are idempotent and can be re-run safely
- Deploy script can be executed multiple times

### Rollback Strategy
```bash
# Quick rollback by destroying and redeploying
./destroy.sh
./deploy.sh

# Partial rollback of applications only
cd ansible && ansible-playbook -i inventory/hosts.yml quickdeploy.yml
```

## Cost Optimization

### Current Costs
- 4 x t3.small instances: ~$0.0208/hour each
- Data transfer: Minimal within same AZ
- Storage: 8 GB per instance included

### Cost Reduction
- Use Spot instances for development
- Implement auto-shutdown scripts
- Consider smaller instance types for testing

## Security

### Network Security
- Security groups restrict access to necessary ports only
- Internal communication uses private IPs
- SSH access limited to key-based authentication

### Application Security
- Secrets stored in AWS Secrets Manager
- No hardcoded credentials in code
- MongoDB authentication required

### Best Practices
- Regular security group audits
- SSH key rotation
- Secret rotation policy
- VPC flow logs for monitoring

## Monitoring and Logging

### Application Logs
```bash
# View real-time logs
docker logs -f metals-producer
docker logs -f metals-processor
```

### Infrastructure Monitoring
- CloudWatch metrics for EC2 instances
- Custom metrics for application health
- Log aggregation through CloudWatch Logs

## CI/CD Integration

This project structure supports integration with CI/CD pipelines:
- Terraform state management for team collaboration
- Ansible playbooks for automated deployment
- Health checks for deployment validation
- Automated testing framework ready

## Pipeline Validation

### Quick Validation
```bash
# Run automated validation
bash scripts/quick-test.sh
```

### Manual Validation Steps

#### 1. Health Endpoint Validation
```bash
# Get VM IPs
cd terraform/
PRODUCER_IP=$(terraform output -raw producer_vm_ip)
PROCESSOR_IP=$(terraform output -raw processor_vm_ip)

# Test producer health
curl -s http://$PRODUCER_IP:8000/health
```
**Expected Output:**
```json
{
  "kafka_connected": true,
  "last_real_fetch": 0,
  "status": "healthy",
  "timestamp": "2025-09-20T04:02:29.838836"
}
```

```bash
# Test processor health
curl -s http://$PROCESSOR_IP:8001/health
```
**Expected Output:**
```json
{
  "error_count": 0,
  "kafka_connected": true,
  "last_processed": null,
  "mongodb_status": "connected",
  "processed_count": 0,
  "status": "healthy",
  "timestamp": "2025-09-20T04:02:30.019143"
}
```

#### 2. Container Status Validation
```bash
cd ansible/

# Check all containers running
ansible -i inventory/hosts.yml all -m shell -a "docker ps"
```
**Expected:** Each VM shows 1-2 containers with "Up" status

```bash
# Verify specific services
ansible -i inventory/hosts.yml kafka -m shell -a "docker ps | grep -E '(kafka|zookeeper)'"
```
**Expected:** 2 containers (kafka and zookeeper) with "Up" status

```bash
ansible -i inventory/hosts.yml database -m shell -a "docker ps | grep mongodb"
```
**Expected:** 1 container (mongodb) with "Up" status

```bash
ansible -i inventory/hosts.yml processor -m shell -a "docker ps | grep metals-processor"
```
**Expected:** 1 container (metals-processor) with "Up" status

```bash
ansible -i inventory/hosts.yml producer -m shell -a "docker ps | grep metals-producer"
```
**Expected:** 1 container (metals-producer) with "Up" status

#### 3. Data Flow Validation
```bash
# Wait for data pipeline to process messages
sleep 120

# Check Kafka topic has messages
ansible -i inventory/hosts.yml kafka -m shell -a "docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic metals-prices --from-beginning --max-messages 1 --timeout-ms 5000"
```
**Expected:** JSON message with metals pricing data

```bash
# Check MongoDB has processed documents
MONGODB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id "metals-mongodb-password" --query SecretString --output text)
ansible -i inventory/hosts.yml database -m shell -a "docker exec mongodb mongosh -u admin -p '$MONGODB_PASSWORD' --authenticationDatabase admin metals --eval 'db.prices.countDocuments({})' --quiet"
```
**Expected:** Number > 0 indicating processed documents

#### 4. End-to-End Smoke Test
```bash
# View sample processed data
ansible -i inventory/hosts.yml database -m shell -a "docker exec mongodb mongosh -u admin -p '$MONGODB_PASSWORD' --authenticationDatabase admin metals --eval 'db.prices.find().limit(1).pretty()' --quiet"
```
**Expected:** Document showing processed metals pricing data

### Troubleshooting Validation Failures

#### Issue: Health Endpoints Return "kafka_connected": false
```bash
# Check Kafka container logs
ansible -i inventory/hosts.yml kafka -m shell -a "docker logs kafka | tail -20"

# Check network connectivity
ansible -i inventory/hosts.yml producer -m shell -a "nc -zv $(terraform output -raw kafka_vm_private_ip) 9092"

# Restart Kafka services
ansible -i inventory/hosts.yml kafka -m shell -a "docker restart kafka zookeeper"
```

#### Issue: No Data in MongoDB
```bash
# Check processor application logs
ansible -i inventory/hosts.yml processor -m shell -a "docker logs metals-processor | tail -20"

# Verify MongoDB connectivity from processor
ansible -i inventory/hosts.yml processor -m shell -a "nc -zv $(terraform output -raw mongodb_vm_private_ip) 27017"

# Check Kafka topic has messages
ansible -i inventory/hosts.yml kafka -m shell -a "docker exec kafka kafka-topics --describe --topic metals-prices --bootstrap-server localhost:9092"
```

#### Issue: Container Not Running
```bash
# Check exit codes and restart reasons
ansible -i inventory/hosts.yml all -m shell -a "docker ps -a"

# View container logs for errors
ansible -i inventory/hosts.yml HOST_GROUP -m shell -a "docker logs CONTAINER_NAME | tail -50"

# Restart specific service
ansible-playbook -i inventory/hosts.yml quickdeploy.yml --limit HOST_GROUP
```

#### Issue: Permission or Network Errors
```bash
# Check security group rules
aws ec2 describe-security-groups --group-names metals-sg

# Test SSH connectivity
ansible -i inventory/hosts.yml all -m ping

# Verify AWS credentials
aws sts get-caller-identity
```

### Validation Checklist
- [ ] All 4 VMs accessible via SSH
- [ ] All containers running (6 total: kafka, zookeeper, mongodb, processor, producer)
- [ ] Health endpoints return "healthy" status
- [ ] Kafka topic "metals-prices" exists and has messages
- [ ] MongoDB contains processed documents
- [ ] No error logs in application containers

## Known Limitations

### Terraform State Management
This implementation uses local Terraform state due to AWS IAM permission restrictions in the educational environment. In a production deployment, the following S3 backend configuration would be recommended:
```hcl
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "ca1/terraform.tfstate"
    region = "us-east-2"
  }
}
```

## License

This project is for educational purposes as part of CS 5287 coursework.
