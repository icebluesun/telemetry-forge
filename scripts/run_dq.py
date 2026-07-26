"""
Data Quality checks using Great Expectations (v3 API).
Runs expectations directly against raw_api_events via pandas,
saves results to dashboard/dq_results.json for the dashboard Quality tab.
"""
import os
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import great_expectations as ge
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
RESULTS_PATH = DASHBOARD_DIR / "dq_results.json"


def run_dq():
    dsn = os.environ["POSTGRES_DSN"]
    engine = create_engine(dsn, pool_pre_ping=True, pool_recycle=300)

    print("Loading sample from raw_api_events...")
    df = pd.read_sql("""
        SELECT event_id, timestamp, user_id, user_tier, endpoint,
               latency_ms, status_code, input_tokens, output_tokens
        FROM raw_api_events
        ORDER BY timestamp DESC
        LIMIT 10000
    """, engine)

    print(f"Loaded {len(df):,} rows. Running expectations...")

    ge_df = ge.from_pandas(df)

    checks = []

    def run(name, result):
        passed = result["success"]
        stats = result.get("result", {})
        checks.append({
            "expectation": name,
            "passed": passed,
            "unexpected_pct": round(stats.get("unexpected_percent", 0), 2),
            "evaluated_count": stats.get("element_count", len(df)),
        })
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    run("event_id not null",
        ge_df.expect_column_values_to_not_be_null("event_id"))

    run("event_id unique",
        ge_df.expect_column_values_to_be_unique("event_id"))

    run("user_id not null",
        ge_df.expect_column_values_to_not_be_null("user_id"))

    run("user_tier in set",
        ge_df.expect_column_values_to_be_in_set(
            "user_tier", ["free", "pro", "enterprise"]))

    run("status_code in set",
        ge_df.expect_column_values_to_be_in_set(
            "status_code", [200, 400, 401, 403, 429, 500, 503, 504]))

    run("latency_ms in range",
        ge_df.expect_column_values_to_be_between(
            "latency_ms", min_value=0, max_value=30000))

    run("input_tokens mean in range",
        ge_df.expect_column_mean_to_be_between(
            "input_tokens", min_value=100, max_value=5000))

    run("endpoint in set",
        ge_df.expect_column_values_to_be_in_set(
            "endpoint", ["/v1/completions", "/v1/chat", "/v1/embeddings", "/v1/classify"]))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    results = {
        "run_time": datetime.now(timezone.utc).isoformat(),
        "row_count": len(df),
        "passed": passed,
        "total": total,
        "checks": checks,
    }

    DASHBOARD_DIR.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ DQ complete: {passed}/{total} checks passed → {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    run_dq()
