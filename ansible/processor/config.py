import os
from typing import List

class Config:
    """Configuration class for metals price processor"""
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: List[str] = os.getenv(
        'KAFKA_BOOTSTRAP_SERVERS', 
        'localhost:9092'
    ).split(',')
    
    KAFKA_TOPIC: str = os.getenv('KAFKA_TOPIC', 'metals-prices')
    KAFKA_GROUP_ID: str = os.getenv('KAFKA_GROUP_ID', 'metals-processor-group')
    
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv(
        'MONGODB_URI', 
        'mongodb://admin:password123@localhost:27017/metals?authSource=admin'
    )
    MONGODB_DATABASE: str = os.getenv('MONGODB_DATABASE', 'metals')
    MONGODB_COLLECTION: str = os.getenv('MONGODB_COLLECTION', 'prices')
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.KAFKA_BOOTSTRAP_SERVERS:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS must be set")
        
        if not cls.KAFKA_TOPIC:
            raise ValueError("KAFKA_TOPIC must be set")
        
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI must be set")