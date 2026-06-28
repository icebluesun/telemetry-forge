"""
Kafka producer that streams synthetic events to a configured Aiven Kafka topic.
Reads connection details from environment variables.
"""
import os
import json
import time
from datetime import datetime, timezone, timedelta
from kafka import KafkaProducer
# from kafka.errors import NoBrokersAvailable
from generator import APITelemetryGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (set in GitHub secrets or local .env)
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "").split(",")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "api_events")

# Create producer with SASL/SSL configuration
def create_producer():
    if not KAFKA_BROKERS or not KAFKA_USERNAME or not KAFKA_PASSWORD:
        raise ValueError("Missing Kafka environment variables.")
    
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKERS,
        security_protocol="SASL_SSL",
        sasl_mechanism="SCRAM-SHA-256",
        sasl_plain_username=KAFKA_USERNAME,
        sasl_plain_password=KAFKA_PASSWORD,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=3,
    )
    return producer

def stream_events(producer, generator, num_events=1000, batch_size=100, delay=0.1):
    """Generate and send events in batches."""
    start_time = datetime.now(timezone.utc)
    sent = 0
    while sent < num_events:
        batch = generator.generate_batch(min(batch_size, num_events - sent), start_time)
        for event in batch:
            try:
                future = producer.send(KAFKA_TOPIC, value=event)
                future.get(timeout=5)
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
                break
        start_time = datetime.fromisoformat(batch[-1]["timestamp"]) + timedelta(milliseconds=10)
        time.sleep(delay)
        logger.info(f"Sent {sent} events so far")
    producer.flush()
    logger.info("Streaming complete.")

def stream_events_10s(producer, generator, days=90):
    """Generate 1 event every 10 seconds for N days (churn-aware)."""
    start = datetime.now(timezone.utc) - timedelta(days=days)
    total_events = days * 24 * 60 * 6  # 6 per minute
    
    logger.info(f"Generating {total_events} events over {days} days")
    
    sent = 0
    for day in range(days):
        day_start = start + timedelta(days=day)
        
        # Generate events for this day
        # Number of events per day varies (some days have more traffic)
        events_per_day = random.randint(8000, 12000)
        
        for i in range(events_per_day):
            timestamp = day_start + timedelta(seconds=i * 10)
            event = generator.generate_event(timestamp)
            producer.send(KAFKA_TOPIC, value=event)
            sent += 1
            
            if sent % 1000 == 0:
                logger.info(f"Sent {sent} events")
        
        # Small delay between days
        time.sleep(0.1)
    
    producer.flush()
    logger.info(f"Done. Sent {sent} total events.")

if __name__ == "__main__":
    import random
    gen = APITelemetryGenerator(seed=42, churn_rate=0.15)
    producer = create_producer()
    stream_events_10s(producer, gen, days=90)