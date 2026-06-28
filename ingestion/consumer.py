"""
Kafka consumer that reads events and writes to PostgreSQL.
Keeps only last 90 days of data (auto-cull).
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from kafka import KafkaConsumer
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "").split(",")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "api_events")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_api_events (
    event_id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id TEXT NOT NULL,
    user_tier TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency_ms NUMERIC(10,2) NOT NULL,
    status_code INTEGER NOT NULL,
    error_type TEXT,
    sdk_version TEXT NOT NULL,
    region TEXT NOT NULL,
    session_id TEXT NOT NULL,
    rate_limited BOOLEAN NOT NULL,
    will_churn BOOLEAN,
    churn_day INTEGER,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_raw_events_timestamp ON raw_api_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_events_user_id ON raw_api_events(user_id);
"""

class PostgresIngester:
    def __init__(self, dsn: str):
        self.engine = create_engine(dsn)
        self._init_table()

    def _init_table(self):
        with self.engine.connect() as conn:
            conn.execute(text(CREATE_TABLE_SQL))
            conn.commit()
            logger.info("PostgreSQL table initialized.")

    def upsert_events(self, events: list):
        if not events:
            return
        
        columns = ["event_id", "timestamp", "user_id", "user_tier", "endpoint",
                   "model_variant", "input_tokens", "output_tokens", "latency_ms",
                   "status_code", "error_type", "sdk_version", "region", "session_id",
                   "rate_limited", "will_churn", "churn_day"]
        values = []
        for e in events:
            ts = datetime.fromisoformat(e["timestamp"])
            values.append((
                e["event_id"], ts, e["user_id"], e["user_tier"], e["endpoint"],
                e["model_variant"], e["input_tokens"], e["output_tokens"], e["latency_ms"],
                e["status_code"], e["error_type"], e["sdk_version"], e["region"],
                e["session_id"], e["rate_limited"],
                e.get("will_churn", False),
                e.get("churn_day", None)
            ))
        
        insert_sql = f"""
            INSERT INTO raw_api_events ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (event_id) DO NOTHING
        """
        
        conn = self.engine.raw_connection()
        try:
            cur = conn.cursor()
            execute_values(cur, insert_sql, values, page_size=100)
            conn.commit()
            logger.info(f"Ingested {len(values)} events.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error ingesting events: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def delete_older_than(self, days=90):
        """Auto-cull: delete events older than N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self.engine.connect() as conn:
            result = conn.execute(
                text("DELETE FROM raw_api_events WHERE timestamp < :cutoff"),
                {"cutoff": cutoff}
            )
            conn.commit()
            if result.rowcount > 0:
                logger.info(f"Deleted {result.rowcount} old events (older than {days} days)")

def consume_and_ingest():
    if not POSTGRES_DSN:
        raise ValueError("POSTGRES_DSN not set")
    
    ingester = PostgresIngester(POSTGRES_DSN)
    
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        security_protocol="SASL_SSL",
        sasl_mechanism="SCRAM-SHA-256",
        sasl_plain_username=KAFKA_USERNAME,
        sasl_plain_password=KAFKA_PASSWORD,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="api_ingestion_group"
    )
    
    batch = []
    BATCH_SIZE = 100
    try:
        for message in consumer:
            event = message.value
            batch.append(event)
            if len(batch) >= BATCH_SIZE:
                ingester.upsert_events(batch)
                ingester.delete_older_than(90)
                consumer.commit()
                batch = []
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        if batch:
            ingester.upsert_events(batch)
            ingester.delete_older_than(90)
            consumer.commit()
        consumer.close()

if __name__ == "__main__":
    consume_and_ingest()