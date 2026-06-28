"""
Kafka producer that streams synthetic events to a configured Aiven Kafka topic.
Reads connection details from environment variables.
"""
import os
import tempfile
import json
import time
import random
from datetime import datetime, timezone, timedelta
from kafka import KafkaProducer
from generator import APITelemetryGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "api_events")
KAFKA_CA_CERT = os.getenv("KAFKA_CA_CERT")

# DEBUG: Check if certificate is loaded
print("=== DEBUG ===")
print(f"KAFKA_BROKERS: {KAFKA_BROKERS}")
print(f"KAFKA_USERNAME: {KAFKA_USERNAME}")
print(f"KAFKA_TOPIC: {KAFKA_TOPIC}")
print(f"CA_CERT length: {len(KAFKA_CA_CERT) if KAFKA_CA_CERT else 0}")

# Write certificate to temp file if provided
ca_cert_path = None
if KAFKA_CA_CERT:
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
        f.write(KAFKA_CA_CERT)
        ca_cert_path = f.name
        print(f"Certificate written to: {ca_cert_path}")
        print(f"Cert starts with: {KAFKA_CA_CERT[:100]}")
else:
    print("No certificate found in environment")

def create_producer():
    if not KAFKA_BROKERS or not KAFKA_USERNAME or not KAFKA_PASSWORD:
        raise ValueError("Missing Kafka environment variables.")
    
    broker_list = [b.strip() for b in KAFKA_BROKERS.split(',') if b.strip()]
    print(f"Broker list: {broker_list}")
    
    producer_config = {
        'bootstrap_servers': broker_list,
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'SCRAM-SHA-256',
        'sasl_plain_username': KAFKA_USERNAME,
        'sasl_plain_password': KAFKA_PASSWORD,
        'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
        'acks': 'all',
        'retries': 3,
    }
    
    if ca_cert_path:
        producer_config['ssl_cafile'] = ca_cert_path
        print(f"Using SSL CA file: {ca_cert_path}")
    else:
        print("WARNING: No SSL CA file provided")
    
    try:
        producer = KafkaProducer(**producer_config)
        print("Producer created successfully")
        return producer
    except Exception as e:
        print(f"Failed to create producer: {e}")
        raise

def stream_events_10s(producer, generator, days=90):
    """Generate 1 event every 10 seconds for N days."""
    start = datetime.now(timezone.utc) - timedelta(days=days)
    total_events = days * 24 * 60 * 6  # 6 per minute
    
    logger.info(f"Generating {total_events} events over {days} days")
    
    sent = 0
    for day in range(days):
        day_start = start + timedelta(days=day)
        events_per_day = random.randint(8000, 12000)
        
        for i in range(events_per_day):
            timestamp = day_start + timedelta(seconds=i * 10)
            event = generator.generate_event(timestamp)
            producer.send(KAFKA_TOPIC, value=event)
            sent += 1
            
            if sent % 1000 == 0:
                logger.info(f"Sent {sent} events")
        
        time.sleep(0.1)
    
    producer.flush()
    logger.info(f"Done. Sent {sent} total events.")

if __name__ == "__main__":
    gen = APITelemetryGenerator(seed=42, churn_rate=0.15)
    producer = create_producer()
    stream_events_10s(producer, gen, days=1)