import subprocess
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent

def run():
    print("🚀 Running full pipeline...")
    
    # Wait 5 seconds for PostgreSQL to start
    print("⏳ Waiting for PostgreSQL to be ready...")
    time.sleep(5)
    
    scripts = [
        ("scripts/run_generator.py", "Generating data..."),
        ("scripts/run_dbt.py", "Running dbt..."),
        ("scripts/run_ml.py", "Training ML..."),
        ("scripts/run_dashboard.py", "Starting dashboard..."),
    ]
    
    for script, msg in scripts:
        print(f"\n{'='*50}\n{msg}")
        result = subprocess.run(
            [sys.executable, script],
            cwd=project_root
        )
        if result.returncode != 0:
            print(f"❌ {script} failed")
            break

if __name__ == "__main__":
    run()