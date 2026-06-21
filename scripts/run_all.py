# run_all.py
import subprocess

def run():
    print("🚀 Running full pipeline...")
    subprocess.run(["python", "run_generator.py"])
    subprocess.run(["python", "run_ml.py"])
    subprocess.run(["python", "run_dashboard.py"])

if __name__ == "__main__":
    run()