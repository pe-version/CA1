#!/bin/bash
set -e

echo "=== DESTROYING METALS PIPELINE ==="

cd terraform/
terraform destroy -auto-approve

echo "All resources destroyed!"

# Verify cleanup
echo "Checking for any remaining instances..."
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*metals*" "Name=instance-state-name,Values=running" \
  --region us-east-2 \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text

echo "If any instances listed above, they need manual cleanup!"
echo "Destruction complete."
