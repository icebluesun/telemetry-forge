# scripts/run_ml.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Get project root
project_root = Path(__file__).parent.parent

# Add paths so Python can find ml_models modules
sys.path.insert(0, str(project_root / "ml_models"))
sys.path.insert(0, str(project_root))

os.environ["POSTGRES_DSN"] = "postgresql://postgres:postgres@localhost:5432/api_analytics_dev"

def run():
    print("🤖 Training ML models...")
    print("=" * 50)
    
    # 1. Anomaly Detection
    print("\n1. Training Anomaly Detector...")
    try:
        from anomaly_detection import train_anomaly_detector
        model = train_anomaly_detector()
        print("   ✅ Anomaly detector trained successfully")
    except Exception as e:
        print(f"   ❌ Anomaly detector failed: {e}")
    
    # 2. Churn Prediction
    print("\n2. Training Churn Prediction Model...")
    try:
        from churn_prediction import train_churn_model
        model, importances = train_churn_model()
        print("   ✅ Churn model trained successfully")
        print(f"   Top features: {list(importances.keys())[:3]}")
    except Exception as e:
        print(f"   ❌ Churn model failed: {e}")
    
    # 3. Survival Analysis
    print("\n3. Fitting Survival Curves...")
    try:
        from survival_analysis import fit_survival_curves
        survival_data = fit_survival_curves()
        print(f"   ✅ Survival curves fitted ({len(survival_data)} data points)")
    except Exception as e:
        print(f"   ❌ Survival analysis failed: {e}")
    
    # 4. Causal Inference (optional)
    print("\n4. Running Causal Inference...")
    try:
        from causal_inference import run_diff_in_diff
        report = run_diff_in_diff()
        print("   ✅ Causal inference complete")
        # Save report
        with open(project_root / "dashboard" / "causal_report.md", "w") as f:
            f.write(report)
    except Exception as e:
        print(f"   ❌ Causal inference failed: {e}")
    
    # 5. LLM Narrative (optional)
    print("\n5. Generating LLM Narrative...")
    try:
        from llm_narrative import generate_narrative
        narrative = generate_narrative()
        print("   ✅ Narrative generated")
        # Save narrative for dashboard
        with open(project_root / "dashboard" / "narrative.txt", "w") as f:
            f.write(narrative)
    except Exception as e:
        print(f"   ❌ Narrative generation failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 ML training complete!")

if __name__ == "__main__":
    run()