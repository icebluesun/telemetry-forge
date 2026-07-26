"""
Kafka producer — batch sender.
Sends a list of events to Kafka and exits cleanly.
Connection details from environment variables.
"""
import os
import json
import tempfile
import logging
from kafka import KafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "api_events")
KAFKA_CA_CERT = os.getenv("KAFKA_CA_CERT", "")


def _write_ca_cert():
    if not KAFKA_CA_CERT:
        return None
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
        f.write(KAFKA_CA_CERT)
        return f.name


def create_producer():
    if not KAFKA_BROKERS or not KAFKA_USERNAME or not KAFKA_PASSWORD:
        raise ValueError("Missing Kafka environment variables.")

    broker_list = [b.strip() for b in KAFKA_BROKERS.split(',') if b.strip()]
    ca_cert_path = _write_ca_cert()

    config = {
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
        config['ssl_cafile'] = ca_cert_path

    return KafkaProducer(**config)


def send_events(events: list):
    """Send a batch of events to Kafka and flush. Exits cleanly."""
    if not events:
        logger.info("No events to send.")
        return

    producer = create_producer()
    for i, event in enumerate(events):
        producer.send(KAFKA_TOPIC, value=event)
        if (i + 1) % 1000 == 0:
            logger.info(f"  Sent {i + 1:,}/{len(events):,} events to Kafka...")

    producer.flush()
    producer.close()
    logger.info(f"✅ Sent {len(events):,} events to Kafka topic '{KAFKA_TOPIC}'.")
