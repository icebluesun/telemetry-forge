"""
Local pipeline test — runs each step in sequence with timing and pass/fail output.
Run from the project root: python test_pipeline_local.py

Requires .env to be present with POSTGRES_DSN, DBT_* and MLFLOW_* vars set.
"""
import subprocess
import sys
import time
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).parent

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD  = "\033[1m"

results = []

def step(name, cmd, cwd=None, skip_reason=None):
    if skip_reason:
        print(f"\n{YELLOW}[SKIP]{RESET} {name} — {skip_reason}")
        results.append((name, "SKIP", 0))
        return True

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}STEP: {name}{RESET}")
    print(f"CMD:  {' '.join(cmd)}")
    print(f"CWD:  {cwd or ROOT}")
    print()

    start = time.time()
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"\n{GREEN}[PASS]{RESET} {name} ({elapsed:.1f}s)")
        results.append((name, "PASS", elapsed))
        return True
    else:
        print(f"\n{RED}[FAIL]{RESET} {name} — exit code {result.returncode} ({elapsed:.1f}s)")
        results.append((name, "FAIL", elapsed))
        return False


def check_env():
    required = ["POSTGRES_DSN", "DBT_HOST", "DBT_USER", "DBT_PASSWORD", "DBT_DBNAME"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"{RED}Missing env vars: {', '.join(missing)}{RESET}")
        print("Make sure .env is in the project root and has these set.")
        sys.exit(1)
    print(f"{GREEN}Env vars OK{RESET}")


if __name__ == "__main__":
    print(f"{BOLD}TelemetryForge — Local Pipeline Test{RESET}")
    print(f"Python: {sys.executable}")
    print(f"Root:   {ROOT}")
    check_env()

    # Quick smoke test: can we reach Postgres?
    print(f"\n{BOLD}Pre-check: Postgres connectivity{RESET}")
    check = subprocess.run(
        [sys.executable, "-c",
         "import os; from sqlalchemy import create_engine, text; "
         "e = create_engine(os.environ['POSTGRES_DSN']); "
         "e.connect().execute(text('SELECT 1')); print('Postgres OK')"],
        cwd=ROOT
    )
    if check.returncode != 0:
        print(f"{RED}Cannot reach Postgres — aborting. Check POSTGRES_DSN.{RESET}")
        sys.exit(1)

    # ── Step 1: Data generation (1 day only for speed) ──────────────────────
    # Temporarily patch days to 1 for local test to avoid 90-day full reload
    print(f"\n{YELLOW}Note: run_generator.py will generate 90 days of data (upsert-safe but slow).{RESET}")
    print(f"{YELLOW}To speed this up, temporarily set days=1 in scripts/run_generator.py.{RESET}")
    step(
        "Generate & ingest events",
        [sys.executable, "scripts/run_generator.py"],
    )

    # ── Step 2: dbt ──────────────────────────────────────────────────────────
    ok = step("dbt deps", ["dbt", "deps", "--profiles-dir", "."], cwd=ROOT / "dbt")
    if ok:
        step("dbt run", ["dbt", "run", "--profiles-dir", "."], cwd=ROOT / "dbt")
        step("dbt test", ["dbt", "test", "--profiles-dir", "."], cwd=ROOT / "dbt")

    # ── Step 3: ML training ──────────────────────────────────────────────────
    step(
        "ML training (train_all.py)",
        [sys.executable, "train_all.py"],
        cwd=ROOT / "ml_models",
    )

    # ── Step 4: Check outputs landed in dashboard/ ──────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}STEP: Check dashboard output files{RESET}")
    ok = True
    for fname in ["narrative.txt", "causal_report.md"]:
        path = ROOT / "dashboard" / fname
        if path.exists():
            print(f"  {GREEN}✓{RESET} dashboard/{fname} ({path.stat().st_size} bytes)")
        else:
            print(f"  {RED}✗{RESET} dashboard/{fname} — MISSING")
            ok = False
    results.append(("Dashboard outputs", "PASS" if ok else "FAIL", 0))

    # ── Step 5: Keep-alive ping ──────────────────────────────────────────────
    hf_url = os.getenv("HF_SPACE_URL", "")
    if hf_url:
        step("Keep-alive ping", ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", hf_url])
    else:
        step("Keep-alive ping", [], skip_reason="HF_SPACE_URL not set in .env (optional)")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}{RESET}")
    for name, status, elapsed in results:
        colour = GREEN if status == "PASS" else (YELLOW if status == "SKIP" else RED)
        timing = f"({elapsed:.1f}s)" if elapsed else ""
        print(f"  {colour}[{status}]{RESET}  {name} {timing}")

    failed = [r for r in results if r[1] == "FAIL"]
    if failed:
        print(f"\n{RED}{len(failed)} step(s) failed. Fix before pushing to GitHub.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All steps passed. Safe to commit and push.{RESET}")
