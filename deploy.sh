#!/bin/bash
set -e

echo "=== DEPLOYING METALS PIPELINE WITH SECRETS ==="

# Get MongoDB password from AWS Secrets Manager
MONGODB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id "metals-mongodb-password" --query SecretString --output text)

# Deploy infrastructure
echo "1. Deploying infrastructure..."
cd terraform/
terraform init -input=false
terraform apply -auto-approve
terraform output -json > ../ansible/terraform-outputs.json

# Deploy applications
echo "2. Deploying applications..."
cd ../ansible/
MONGODB_PASSWORD="$MONGODB_PASSWORD" ansible-playbook -i inventory/hosts.yml quickdeploy.yml -e "mongodb_password=$MONGODB_PASSWORD"

echo "3. Testing deployment..."
sleep 60
cd ../terraform/
PRODUCER_IP=$(terraform output -raw producer_vm_ip)
PROCESSOR_IP=$(terraform output -raw processor_vm_ip)
curl -s http://$PRODUCER_IP:8000/health
curl -s http://$PROCESSOR_IP:8001/health

echo "Deployment complete!"
