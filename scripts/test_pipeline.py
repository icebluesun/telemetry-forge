import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "data_generation"))
sys.path.insert(0, str(project_root / "ingestion"))

from generator import APITelemetryGenerator
from consumer import PostgresIngester

def test_pipeline():
    """Test the pipeline locally."""
    
    # Set database connection
    dsn = "postgresql://postgres:postgres@localhost:5432/api_analytics_dev"
    os.environ["POSTGRES_DSN"] = dsn
    
    print("📊 Testing pipeline...")
    
    # 1. Generate events
    print("Generating events...")
    gen = APITelemetryGenerator(seed=42)
    now = datetime.now(timezone.utc)
    
    all_events = []
    for day in range(7):
        day_start = now - timedelta(days=day)
        batch = gen.generate_batch(50, day_start)
        all_events.extend(batch)
    
    print(f"✅ Generated {len(all_events)} events")
    
    # 2. Ingest to PostgreSQL
    print("Ingesting to PostgreSQL...")
    ingester = PostgresIngester(dsn)
    ingester.upsert_events(all_events)
    
    # 3. Verify
    engine = create_engine(dsn)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM raw_api_events")).scalar()
        print(f"✅ Database now has {count} events")
    
    print("🎉 Pipeline test complete!")

if __name__ == "__main__":
    test_pipeline()