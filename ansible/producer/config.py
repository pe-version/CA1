import os
from typing import List

class Config:
    """Configuration class for metals price producer"""
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: List[str] = os.getenv(
        'KAFKA_BOOTSTRAP_SERVERS', 
        'localhost:9092'
    ).split(',')
    
    KAFKA_TOPIC: str = os.getenv('KAFKA_TOPIC', 'metals-prices')
    
    # API Configuration
    API_KEY: str = os.getenv('API_KEY', '')
    
    # Timing Configuration
    FETCH_INTERVAL: int = int(os.getenv('FETCH_INTERVAL', '300'))  # 5 minutes default
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.KAFKA_BOOTSTRAP_SERVERS:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS must be set")
        
        if not cls.KAFKA_TOPIC:
            raise ValueError("KAFKA_TOPIC must be set")
        
        if cls.FETCH_INTERVAL < 60:
            raise ValueError("FETCH_INTERVAL must be at least 60 seconds")