output "kafka_vm_ip" {
  value = aws_instance.kafka_vm.public_ip
}

output "kafka_vm_private_ip" {
  value = aws_instance.kafka_vm.private_ip
}

output "mongodb_vm_ip" {
  value = aws_instance.mongodb_vm.public_ip
}

output "mongodb_vm_private_ip" {
  value = aws_instance.mongodb_vm.private_ip
}

output "processor_vm_ip" {
  value = aws_instance.processor_vm.public_ip
}

output "processor_vm_private_ip" {
  value = aws_instance.processor_vm.private_ip
}

output "producer_vm_ip" {
  value = aws_instance.producer_vm.public_ip
}

output "producer_vm_private_ip" {
  value = aws_instance.producer_vm.private_ip
}