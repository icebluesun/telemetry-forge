# scripts/run_generator.py
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "data_generation"))
sys.path.insert(0, str(project_root / "ingestion"))

from generator import APITelemetryGenerator
from consumer import PostgresIngester
from datetime import datetime, timezone, timedelta

os.environ["POSTGRES_DSN"] = "postgresql://postgres:postgres@localhost:5432/api_analytics_dev"

def run():
    print("📊 Generating 90 days of data with churn...")
    
    # Create generator with churn
    gen = APITelemetryGenerator(seed=42, churn_rate=0.15)
    ingester = PostgresIngester(os.environ["POSTGRES_DSN"])
    
    start = datetime.now(timezone.utc) - timedelta(days=90)
    all_events = []
    total_events = 90 * 24 * 6  # 90 days × 24 hours × 6 events/hour
    
    print(f"Generating {total_events} events...")
    
    for i in range(total_events):
        timestamp = start + timedelta(seconds=i * 10)
        event = gen.generate_event(timestamp)
        all_events.append(event)
        
        if i % 1000 == 0:
            print(f"Generated {i}/{total_events} events")
    
    print(f"Generated {len(all_events)} events")
    print("Ingesting to PostgreSQL...")
    ingester.upsert_events(all_events)
    print(f"✅ Done! {len(all_events)} events with churn data")

if __name__ == "__main__":
    run()