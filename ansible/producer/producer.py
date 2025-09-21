# producer.py
import json
import time
import logging
import requests
import random
from datetime import datetime
from kafka import KafkaProducer
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

class MetalsProducer:
    def __init__(self):
        self.config = Config()
        self.kafka_producer = None
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Base prices for simulation (real API calls will override these)
        self.base_prices = {
            'GOLD': 1850.00,
            'SILVER': 24.50,
            'COPPER': 8500.00,
            'PLATINUM': 950.00,
            'ALUMINUM': 1850.00
        }
        
        # Track last real API call
        self.last_real_fetch = 0
        self.real_fetch_interval = 3600  # Fetch real data every hour
        
    def setup_kafka_producer(self):
        """Initialize Kafka producer with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=5,
                    acks='all'
                )
                logger.info("Kafka producer initialized successfully")
                return True
            except Exception as e:
                logger.warning(f"Kafka connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("Failed to connect to Kafka after all retries")
                    return False
    
    def fetch_real_prices(self):
        """Fetch real metals prices from MetalpriceAPI"""
        try:
            if not self.config.API_KEY:
                logger.warning("No API key configured, using simulated data only")
                return None
                
            # MetalpriceAPI endpoint and headers
            url = "https://api.metalpriceapi.com/v1/latest"
            headers = {
                "X-API-KEY": self.config.API_KEY,
                "Content-Type": "application/json"
            }
            
            # Request metals: XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium)
            params = {
                "base": "USD",
                "currencies": "XAU,XAG,XPT,XPD"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully fetched real metals prices from MetalpriceAPI")
                self.last_real_fetch = time.time()
                return self.parse_metalpriceapi_response(data)
            else:
                logger.warning(f"MetalpriceAPI request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.warning(f"MetalpriceAPI request failed: {e}")
            return None

    def parse_metalpriceapi_response(self, api_data):
        """Parse MetalpriceAPI response into standard format"""
        try:
            parsed_prices = {}
            
            if 'success' in api_data and api_data['success'] and 'rates' in api_data:
                rates = api_data['rates']
                
                # MetalpriceAPI returns rates as 1/price for metals
                # XAU, XAG, XPT, XPD are metals (need to calculate 1/rate for USD price)
                metal_mapping = {
                    'XAU': 'GOLD',
                    'XAG': 'SILVER', 
                    'XPT': 'PLATINUM',
                    'XPD': 'PALLADIUM'
                }
                
                for api_symbol, our_symbol in metal_mapping.items():
                    if api_symbol in rates:
                        # MetalpriceAPI returns rates where 1 USD = X metal units
                        # We want price per unit, so we calculate 1/rate
                        rate = rates[api_symbol]
                        if rate > 0:
                            price_per_unit = 1 / rate
                            parsed_prices[our_symbol] = round(price_per_unit, 2)
                            
            return parsed_prices if parsed_prices else None
            
        except Exception as e:
            logger.error(f"Error parsing MetalpriceAPI response: {e}")
            return None
    
    def generate_price_variation(self, metal, base_price):
        """Generate realistic price variation"""
        # Different metals have different volatility patterns
        volatility = {
            'GOLD': 0.015,      # 1.5% max variation
            'SILVER': 0.025,    # 2.5% max variation  
            'COPPER': 0.020,    # 2.0% max variation
            'PLATINUM': 0.030,  # 3.0% max variation
            'ALUMINUM': 0.018   # 1.8% max variation
        }
        
        var_percent = random.uniform(-volatility.get(metal, 0.02), volatility.get(metal, 0.02))
        new_price = base_price * (1 + var_percent)
        return round(new_price, 2)
    
    def generate_price_data(self):
        """Generate price data (real or simulated)"""
        current_time = time.time()
        
        # Try to fetch real data if it's been long enough
        real_prices = None
        if (current_time - self.last_real_fetch) > self.real_fetch_interval:
            real_prices = self.fetch_real_prices()
        
        # Update base prices if we got real data
        if real_prices:
            self.base_prices.update(real_prices)
            logger.info("Updated base prices with real market data")
        
        # Generate current prices (with variations from base)
        metals_data = []
        for metal, base_price in self.base_prices.items():
            current_price = self.generate_price_variation(metal, base_price)
            
            price_data = {
                'metal': metal,
                'price': current_price,
                'currency': 'USD',
                'timestamp': datetime.utcnow().isoformat(),
                'exchange': 'SIMULATION' if not real_prices else 'LIVE',
                'volume': random.randint(1000, 10000),  # Simulated volume
                'change_24h': round(random.uniform(-5.0, 5.0), 2)
            }
            
            metals_data.append(price_data)
        
        return metals_data
    
    def send_to_kafka(self, price_data):
        """Send price data to Kafka topic"""
        try:
            future = self.kafka_producer.send(
                self.config.KAFKA_TOPIC,
                key=price_data['metal'],
                value=price_data
            )
            
            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)
            logger.debug(f"Sent {price_data['metal']} price to Kafka: "
                        f"topic={record_metadata.topic}, partition={record_metadata.partition}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            return False
    
    def run_producer_loop(self):
        """Main producer loop"""
        logger.info("Starting metals price producer...")
        
        if not self.setup_kafka_producer():
            logger.error("Failed to setup Kafka producer, exiting")
            return
        
        while True:
            try:
                # Generate price data for all metals
                metals_data = self.generate_price_data()
                
                # Send each metal's data to Kafka
                success_count = 0
                for price_data in metals_data:
                    if self.send_to_kafka(price_data):
                        success_count += 1
                
                logger.info(f"Sent {success_count}/{len(metals_data)} price updates to Kafka")
                
                # Wait for next iteration
                time.sleep(self.config.FETCH_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in producer loop: {e}")
                time.sleep(30)  # Wait before retrying
        
        # Cleanup
        if self.kafka_producer:
            self.kafka_producer.close()
        logger.info("Producer shutdown complete")
    
    def setup_routes(self):
        """Setup Flask health check routes"""
        @self.app.route('/health')
        def health_check():
            status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'kafka_connected': self.kafka_producer is not None,
                'last_real_fetch': self.last_real_fetch
            }
            return jsonify(status)
        
        @self.app.route('/metrics')
        def metrics():
            return jsonify({
                'base_prices': self.base_prices,
                'last_real_fetch': self.last_real_fetch,
                'fetch_interval': self.config.FETCH_INTERVAL
            })

def run_flask_app(producer):
    """Run Flask health check server in separate thread"""
    producer.app.run(host='0.0.0.0', port=8000, debug=False)

if __name__ == "__main__":
    producer = MetalsProducer()
    
    # Start health check server in background thread
    flask_thread = Thread(target=run_flask_app, args=(producer,), daemon=True)
    flask_thread.start()
    
    # Start main producer loop
    producer.run_producer_loop()
