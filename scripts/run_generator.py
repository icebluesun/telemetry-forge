# scripts/run_generator.py
import os
import sys
import uuid
import random
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
CULL_DAYS = 120

# Namespace for deterministic event_id — same timestamp always = same UUID
EVENT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Time-of-day weights (UTC hour → extra events to add this run)
# Peak business hours get more traffic, nights get less
HOUR_WEIGHTS = {
    0: 5,  1: 3,  2: 2,  3: 2,  4: 3,  5: 5,
    6: 15, 7: 30, 8: 50, 9: 80, 10: 90, 11: 95,
    12: 85, 13: 90, 14: 95, 15: 90, 16: 80, 17: 60,
    18: 40, 19: 30, 20: 20, 21: 15, 22: 10, 23: 7,
}

def get_topup_count(hour_utc: int, is_weekend: bool) -> int:
    """Random extra events for this hourly run based on time of day."""
    base = HOUR_WEIGHTS.get(hour_utc, 10)
    if is_weekend:
        base = int(base * 0.5)
    # Add ±30% noise
    noise = random.uniform(0.7, 1.3)
    return max(0, int(base * noise))


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

    # Step 4: generate events only for missing slots (deterministic backfill)
    all_events = []
    if missing_slots:
        for i, ts in enumerate(sorted(missing_slots)):
            event = gen.generate_event(ts)
            event["event_id"] = make_event_id(ts)
            all_events.append(event)
            if (i + 1) % 5000 == 0:
                print(f"  Generated {i + 1:,}/{len(missing_slots):,} events...")
        print(f"📝 Backfill: {len(all_events):,} events")
    else:
        print("✅ Slot map fully populated — no backfill needed.")

    # Step 5: random top-up for current hour based on time-of-day
    is_weekend = now.weekday() >= 5
    topup_count = get_topup_count(now.hour, is_weekend)
    print(f"🎲 Top-up: +{topup_count} random events for hour {now.hour:02d}:00 UTC (weekend={is_weekend})")

    topup_events = []
    for _ in range(topup_count):
        # Random timestamp within the current hour
        jitter = timedelta(seconds=random.randint(0, 3599))
        ts = now.replace(minute=0, second=0, microsecond=0) + jitter
        event = gen.generate_event(ts)
        # UUID4 — random, not deterministic, so these accumulate naturally
        event["event_id"] = str(uuid.uuid4())
        topup_events.append(event)

    all_events.extend(topup_events)

    if all_events:
        print(f"Ingesting {len(all_events):,} total events...")
        ingester.upsert_events(all_events)
        print(f"✅ Done! {len(all_events):,} events ingested ({len(topup_events)} top-up).")
    else:
        print("✅ Nothing to ingest this run.")


if __name__ == "__main__":
    run()
