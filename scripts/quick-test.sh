```bash
#!/bin/bash

echo "=== QUICK PIPELINE TEST ==="
echo "Starting at $(date)"

# Get IPs from Terraform
cd terraform/
PRODUCER_IP=$(terraform output -raw producer_vm_ip)
PROCESSOR_IP=$(terraform output -raw processor_vm_ip)
KAFKA_IP=$(terraform output -raw kafka_vm_ip)
MONGODB_IP=$(terraform output -raw mongodb_vm_ip)

echo "Testing with IPs:"
echo "Producer: $PRODUCER_IP"
echo "Processor: $PROCESSOR_IP"
echo "Kafka: $KAFKA_IP"
echo "MongoDB: $MONGODB_IP"

# Test 1: Health Endpoints
echo "=== Health Check ==="
curl -s http://$PRODUCER_IP:8000/health && echo "✅ Producer healthy" || echo "❌ Producer failed"
curl -s http://$PROCESSOR_IP:8001/health && echo "✅ Processor healthy" || echo "❌ Processor failed"

# Test 2: Container Status
echo "=== Container Status ==="
ssh ~/.ssh/ca0-keys.pem  ubuntu@$KAFKA_IP "docker ps | grep kafka" && echo "✅ Kafka running"
ssh ~/.ssh/ca0-keys.pem ubuntu@$MONGODB_IP "docker ps | grep mongodb" && echo "✅ MongoDB running"
ssh ~/.ssh/ca0-keys.pem ubuntu@$PROCESSOR_IP "docker ps | grep processor" && echo "✅ Processor running"
ssh ~/.ssh/ca0-keys.pem ubuntu@$PRODUCER_IP "docker ps | grep producer" && echo "✅ Producer running"

# Test 3: Basic Data Flow
echo "=== Data Flow Test ==="
sleep 60  # Wait for some data to flow
COUNT=$(ssh ubuntu@$MONGODB_IP "docker exec mongodb mongosh -u admin -p password123 --authenticationDatabase admin metals --eval 'db.prices.countDocuments({})' --quiet")
echo "MongoDB documents: $COUNT"

if [ "$COUNT" -gt 0 ]; then
    echo "✅ PIPELINE WORKING: $COUNT documents in MongoDB"
else
    echo "❌ PIPELINE ISSUE: No documents found"
fi

echo "=== Test Complete ==="
```
