# Dockerfile for Metals Price Processor (Kafka Consumer)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash metals-user && \
    chown -R metals-user:metals-user /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY processor.py .
COPY config.py .

# Switch to non-root user
USER metals-user

# Environment variables (can be overridden at runtime)
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENV KAFKA_TOPIC=metals-prices
ENV KAFKA_GROUP_ID=metals-processor-group
ENV MONGODB_URI=mongodb://admin:password123@localhost:27017/metals?authSource=admin
ENV MONGODB_DATABASE=metals
ENV MONGODB_COLLECTION=prices
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health', timeout=5)" || exit 1

# Expose health check port
EXPOSE 8001

# Run the processor
CMD ["python", "processor.py"]
