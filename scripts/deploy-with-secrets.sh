#!/bin/bash
set -e

echo "=== DEPLOYING WITH SECRETS ==="

# Get MongoDB password from AWS Secrets Manager
MONGODB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id "metals-mongodb-password" --query SecretString --output text)

if [ -z "$MONGODB_PASSWORD" ]; then
    echo "Failed to retrieve MongoDB password from AWS Secrets Manager"
    exit 1
fi

echo "Retrieved password from AWS Secrets Manager"

# Deploy infrastructure
echo "1. Deploying infrastructure..."
cd terraform/
terraform apply -auto-approve

# Deploy applications with secret
echo "2. Deploying applications with secrets..."
cd ../ansible/

# Pass the password as an environment variable to Ansible
MONGODB_PASSWORD="$MONGODB_PASSWORD" ansible-playbook -i inventory/hosts.yml quickdeploy.yml -e "mongodb_password=$MONGODB_PASSWORD"

echo "Deployment complete with secure password!"
