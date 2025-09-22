#!/bin/bash
set -e

echo "=== DEPLOYING METALS PIPELINE WITH AUTOMATED STATE MANAGEMENT ==="

# Configuration
REGION="us-east-2"

# Note: Using local state due to S3 permissions restrictions
# In production, would use S3 backend for state management
echo "Using local Terraform state (S3 backend requires additional permissions)..."
cd terraform/

# Ensure we have required providers block
if [ ! -f "versions.tf" ]; then
    cat > versions.tf << EOF
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
EOF
fi

# Retrieve all secrets from AWS Secrets Manager
echo "Retrieving secrets from AWS Secrets Manager..."
MONGODB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id "metals-mongodb-password" --query SecretString --output text)
KAFKA_ADMIN_PASSWORD=$(aws secretsmanager get-secret-value --secret-id "metals-kafka-admin-password" --query SecretString --output text)
API_KEY=$(aws secretsmanager get-secret-value --secret-id "metals-api-key" --query SecretString --output text)

# Validate all secrets retrieved
if [ -z "$MONGODB_PASSWORD" ] || [ -z "$KAFKA_ADMIN_PASSWORD" ] || [ -z "$API_KEY" ]; then
    echo "Failed to retrieve one or more secrets from AWS Secrets Manager"
    echo "Required secrets: metals-mongodb-password, metals-kafka-admin-password, metals-api-key"
    exit 1
fi

echo "All secrets retrieved successfully"

# Deploy infrastructure
echo "1. Initializing and deploying infrastructure..."
terraform init -input=false
terraform apply -auto-approve
terraform output -json > ../ansible/terraform-outputs.json

# Deploy applications with all secrets
echo "2. Deploying applications with secrets..."
cd ../ansible/
MONGODB_PASSWORD="$MONGODB_PASSWORD" \
KAFKA_ADMIN_PASSWORD="$KAFKA_ADMIN_PASSWORD" \
API_KEY="$API_KEY" \
ansible-playbook -i inventory/hosts.yml quickdeploy.yml \
  -e "mongodb_password=$MONGODB_PASSWORD" \
  -e "kafka_admin_password=$KAFKA_ADMIN_PASSWORD" \
  -e "api_key=$API_KEY"

echo "3. Testing deployment..."
sleep 60
cd ../terraform/
PRODUCER_IP=$(terraform output -raw producer_vm_ip)
PROCESSOR_IP=$(terraform output -raw processor_vm_ip)

echo "Testing health endpoints:"
curl -s http://$PRODUCER_IP:8000/health && echo "Producer healthy"
curl -s http://$PROCESSOR_IP:8001/health && echo "Processor healthy"

echo ""
echo "Deployment complete!"
echo "Health URLs:"
echo "Producer: http://$PRODUCER_IP:8000/health"
echo "Processor: http://$PROCESSOR_IP:8001/health"
