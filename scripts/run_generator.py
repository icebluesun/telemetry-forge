# scripts/run_generator.py
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "data_generation"))
sys.path.insert(0, str(project_root / "ingestion"))

from generator import APITelemetryGenerator
from consumer import PostgresIngester
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text

RETENTION_DAYS = 90
CULL_DAYS = 120        # cull anything older than this — buffer beyond retention window
EVENTS_PER_HOUR = 60  # 1 event per minute per hour slot

# Namespace for deterministic event_id — same timestamp always = same UUID
EVENT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def get_engine(dsn):
    return create_engine(dsn, pool_pre_ping=True, pool_recycle=300)


def cull_old_data(engine):
    """Delete anything older than CULL_DAYS. Always runs first."""
    with engine.connect() as conn:
        result = conn.execute(text(
            f"DELETE FROM raw_api_events "
            f"WHERE timestamp < NOW() - INTERVAL '{CULL_DAYS} days'"
        ))
        conn.commit()
        print(f"🗑️  Culled {result.rowcount} rows older than {CULL_DAYS} days")


def get_existing_slots(engine, start_dt, end_dt):
    """
    Return a set of existing minute-level timestamps already in the DB
    for the given date range. Each slot = truncated to the minute.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DATE_TRUNC('minute', timestamp) as slot
            FROM raw_api_events
            WHERE timestamp >= :start AND timestamp < :end
        """), {"start": start_dt, "end": end_dt}).fetchall()
    return {row[0].replace(tzinfo=timezone.utc) for row in rows}


def build_expected_slots(start_dt, end_dt):
    """
    Build the full map of expected minute-level timestamps
    for the retention window: 90 days × 24h × 60min.
    """
    slots = []
    ts = start_dt
    interval = timedelta(minutes=1)
    while ts < end_dt:
        slots.append(ts)
        ts += interval
    return slots


def make_event_id(ts: datetime) -> str:
    """Deterministic event_id based on timestamp — same minute = same ID."""
    return str(uuid.uuid5(EVENT_NS, ts.strftime("%Y-%m-%d %H:%M")))


def run():
    dsn = os.environ["POSTGRES_DSN"]
    engine = get_engine(dsn)
    ingester = PostgresIngester(dsn)
    gen = APITelemetryGenerator(seed=42, churn_rate=0.25)

    # Step 1: cull anything older than 120 days
    cull_old_data(engine)

    # Step 2: build the full expected slot map for last 90 days
    now = datetime.now(timezone.utc)
    end_dt = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    start_dt = end_dt - timedelta(days=RETENTION_DAYS)

    print(f"📅 Window: {start_dt.date()} → {end_dt.date()} ({RETENTION_DAYS} days)")

    expected_slots = build_expected_slots(start_dt, end_dt)
    print(f"📊 Expected slots: {len(expected_slots):,}")

    # Step 3: check which slots already exist in DB
    existing_slots = get_existing_slots(engine, start_dt, end_dt)
    print(f"✅ Existing slots: {len(existing_slots):,}")

    missing_slots = [ts for ts in expected_slots if ts not in existing_slots]
    print(f"⚡ Missing slots:  {len(missing_slots):,}")

    if not missing_slots:
        print("Nothing to generate — DB is fully populated for the retention window.")
        return

    # Step 4: generate events only for missing slots
    all_events = []
    for i, ts in enumerate(sorted(missing_slots)):
        event = gen.generate_event(ts)
        # Override event_id with deterministic value so re-runs never duplicate
        event["event_id"] = make_event_id(ts)
        all_events.append(event)
        if (i + 1) % 5000 == 0:
            print(f"  Generated {i + 1:,}/{len(missing_slots):,} events...")

    print(f"Generated {len(all_events):,} events. Ingesting...")
    ingester.upsert_events(all_events)
    print(f"✅ Done! {len(all_events):,} events ingested.")


if __name__ == "__main__":
    run()
