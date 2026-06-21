# run_dashboard.py
import os
import subprocess

os.environ["POSTGRES_DSN"] = "postgresql://postgres:postgres@localhost:5432/api_analytics_dev"

def run():
    print("📊 Starting dashboard...")
    subprocess.run(["streamlit", "run", "dashboard/app.py"])

if __name__ == "__main__":
    run()
    