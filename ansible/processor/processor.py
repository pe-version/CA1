# processor/processor.py
import json
import logging
import time
from datetime import datetime
from kafka import KafkaConsumer
from pymongo import MongoClient, errors
from flask import Flask, jsonify
from threading import Thread
import os
from config import Config

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetalsProcessor:
    def __init__(self):
        self.config = Config()
        self.kafka_consumer = None
        self.mongodb_client = None
        self.database = None
        self.collection = None
        self.app = Flask(__name__)
        self.processed_count = 0
        self.error_count = 0
        self.last_processed = None
        self.setup_routes()
        
    def setup_mongodb_connection(self):
        """Initialize MongoDB connection with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.mongodb_client = MongoClient(
                    self.config.MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000
                )
                
                # Test connection
                self.mongodb_client.admin.command('ping')
                
                # Setup database and collection
                self.database = self.mongodb_client[self.config.MONGODB_DATABASE]
                self.collection = self.database[self.config.MONGODB_COLLECTION]
                
                # Create indices for better query performance
                self.collection.create_index([("metal", 1), ("timestamp", -1)])
                self.collection.create_index([("timestamp", -1)])
                
                logger.info("MongoDB connection established successfully")
                return True
                
            except Exception as e:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("Failed to connect to MongoDB after all retries")
                    return False
    
    def setup_kafka_consumer(self):
        """Initialize Kafka consumer with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.kafka_consumer = KafkaConsumer(
                    self.config.KAFKA_TOPIC,
                    bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                    group_id=self.config.KAFKA_GROUP_ID,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    auto_offset_reset='latest',  # Start from latest messages
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,
                    consumer_timeout_ms=1000  # Timeout for polling
                )
                
                logger.info("Kafka consumer initialized successfully")
                return True
                
            except Exception as e:
                logger.warning(f"Kafka consumer connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("Failed to connect to Kafka consumer after all retries")
                    return False
    
    def process_price_data(self, price_data):
        """Process and enrich price data before storing"""
        try:
            # Add processing timestamp
            price_data['processed_at'] = datetime.utcnow().isoformat()
            
            # Convert timestamp string to datetime object for MongoDB
            if 'timestamp' in price_data:
                if isinstance(price_data['timestamp'], str):
                    price_data['timestamp_dt'] = datetime.fromisoformat(
                        price_data['timestamp'].replace('Z', '+00:00')
                    )
            
            # Add price analysis
            price_data['price_category'] = self.categorize_price(
                price_data['metal'], 
                price_data['price']
            )
            
            # Add market session info
            price_data['market_session'] = self.get_market_session()
            
            # Validate required fields
            required_fields = ['metal', 'price', 'currency', 'timestamp']
            for field in required_fields:
                if field not in price_data or price_data[field] is None:
                    raise ValueError(f"Missing required field: {field}")
            
            return price_data
            
        except Exception as e:
            logger.error(f"Error processing price data: {e}")
            raise
    
    def categorize_price(self, metal, price):
        """Categorize price as high/medium/low based on historical ranges"""
        # Simple price categorization - in production, this would use historical data
        thresholds = {
            'GOLD': {'low': 1800, 'high': 2000},
            'SILVER': {'low': 20, 'high': 30},
            'COPPER': {'low': 8000, 'high': 9000},
            'PLATINUM': {'low': 900, 'high': 1100},
            'ALUMINUM': {'low': 1700, 'high': 2000}
        }
        
        if metal in thresholds:
            if price <= thresholds[metal]['low']:
                return 'low'
            elif price >= thresholds[metal]['high']:
                return 'high'
            else:
                return 'medium'
        
        return 'unknown'
    
    def get_market_session(self):
        """Determine current market session"""
        current_hour = datetime.utcnow().hour
        
        if 13 <= current_hour < 21:  # 1 PM - 9 PM UTC (approx US trading hours)
            return 'us_session'
        elif 7 <= current_hour < 16:  # 7 AM - 4 PM UTC (approx London trading hours)
            return 'london_session'
        elif 23 <= current_hour or current_hour < 8:  # 11 PM - 8 AM UTC (approx Asia session)
            return 'asia_session'
        else:
            return 'overlap_session'
    
    def store_to_mongodb(self, processed_data):
        """Store processed data to MongoDB"""
        try:
            # Insert document
            result = self.collection.insert_one(processed_data)
            
            if result.inserted_id:
                logger.debug(f"Stored {processed_data['metal']} price data to MongoDB: {result.inserted_id}")
                return True
            else:
                logger.error("Failed to insert document to MongoDB")
                return False
                
        except errors.DuplicateKeyError:
            logger.warning("Duplicate price data, skipping insert")
            return True
        except Exception as e:
            logger.error(f"Error storing data to MongoDB: {e}")
            return False
    
    def run_processor_loop(self):
        """Main processor loop"""
        logger.info("Starting metals price processor...")
        
        # Setup connections
        if not self.setup_mongodb_connection():
            logger.error("Failed to setup MongoDB connection, exiting")
            return
        
        if not self.setup_kafka_consumer():
            logger.error("Failed to setup Kafka consumer, exiting")
            return
        
        logger.info("Starting to consume messages from Kafka...")
        
        try:
            while True:
                try:
                    # Poll for messages
                    message_batch = self.kafka_consumer.poll(timeout_ms=1000)
                    
                    if not message_batch:
                        continue  # No messages, continue polling
                    
                    # Process messages
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            self.process_message(message)
                    
                except Exception as e:
                    logger.error(f"Error in processor loop: {e}")
                    self.error_count += 1
                    time.sleep(5)  # Brief pause before continuing
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.cleanup()
    
    def process_message(self, message):
        """Process individual Kafka message"""
        try:
            price_data = message.value
            logger.debug(f"Received message for {price_data.get('metal', 'unknown')}")
            
            # Process the price data
            processed_data = self.process_price_data(price_data)
            
            # Store to MongoDB
            if self.store_to_mongodb(processed_data):
                self.processed_count += 1
                self.last_processed = datetime.utcnow().isoformat()
                
                if self.processed_count % 10 == 0:  # Log every 10th message
                    logger.info(f"Processed {self.processed_count} messages successfully")
            else:
                self.error_count += 1
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.error_count += 1
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        if self.kafka_consumer:
            self.kafka_consumer.close()
            logger.info("Kafka consumer closed")
        
        if self.mongodb_client:
            self.mongodb_client.close()
            logger.info("MongoDB connection closed")
        
        logger.info("Processor shutdown complete")
    
    def setup_routes(self):
        """Setup Flask health check and metrics routes"""
        @self.app.route('/health')
        def health_check():
            mongodb_connected = self.mongodb_client is not None
            kafka_connected = self.kafka_consumer is not None
            
            # Test MongoDB connection
            if mongodb_connected:
                try:
                    self.mongodb_client.admin.command('ping')
                    mongodb_status = 'connected'
                except:
                    mongodb_status = 'disconnected'
            else:
                mongodb_status = 'not_initialized'
            
            status = {
                'status': 'healthy' if mongodb_connected and kafka_connected else 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'mongodb_status': mongodb_status,
                'kafka_connected': kafka_connected,
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'last_processed': self.last_processed
            }
            return jsonify(status)
        
        @self.app.route('/metrics')
        def metrics():
            # Get some basic collection stats
            collection_stats = {}
            if self.collection:
                try:
                    collection_stats = {
                        'total_documents': self.collection.count_documents({}),
                        'unique_metals': len(self.collection.distinct('metal')),
                        'latest_timestamp': None
                    }
                    
                    # Get latest document
                    latest_doc = self.collection.find_one(
                        sort=[('timestamp_dt', -1)]
                    )
                    if latest_doc and 'timestamp' in latest_doc:
                        collection_stats['latest_timestamp'] = latest_doc['timestamp']
                        
                except Exception as e:
                    logger.error(f"Error getting collection stats: {e}")
            
            return jsonify({
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'last_processed': self.last_processed,
                'collection_stats': collection_stats
            })

def run_flask_app(processor):
    """Run Flask health check server in separate thread"""
    processor.app.run(host='0.0.0.0', port=8001, debug=False)

if __name__ == "__main__":
    processor = MetalsProcessor()
    
    # Start health check server in background thread
    flask_thread = Thread(target=run_flask_app, args=(processor,), daemon=True)
    flask_thread.start()
    
    # Start main processor loop
    processor.run_processor_loop()

# processor/config.py
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
