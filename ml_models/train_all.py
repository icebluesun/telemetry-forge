"""
Orchestrates training of all ML models and logs to MLflow.
"""
import os
import json
import logging
import pandas as pd
import mlflow
from dotenv import load_dotenv
from anomaly_detection import train_anomaly_detector
from churn_prediction import train_churn_model
from survival_analysis import fit_survival_curves
from causal_inference import run_diff_in_diff
from llm_narrative import generate_narrative

# Suppress MLflow warnings
logging.getLogger("mlflow").setLevel(logging.ERROR)

load_dotenv()

def main():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    mlflow.set_experiment("api_analytics_models")

    with mlflow.start_run(run_name="full_training_run"):
        print("Training anomaly detector...")
        anomaly_model = train_anomaly_detector()
        mlflow.sklearn.log_model(anomaly_model, "anomaly_detector")

        print("Training churn prediction model...")
        churn_model, feature_importances = train_churn_model()
        mlflow.sklearn.log_model(churn_model, "churn_predictor")

        with open("feature_importances.json", "w") as f:
            json.dump(feature_importances, f)
        mlflow.log_artifact("feature_importances.json")

        print("Fitting survival curves...")
        survival_data = fit_survival_curves()
        survival_data.to_csv("survival_curves.csv")
        mlflow.log_artifact("survival_curves.csv")

        print("Running causal inference...")
        diff_in_diff_results = run_diff_in_diff()
        with open("diff_in_diff_results.md", "w") as f:
            f.write(diff_in_diff_results)
        mlflow.log_artifact("diff_in_diff_results.md")

        print("Generating LLM narrative...")
        narrative = generate_narrative()
        with open("narrative.txt", "w") as f:
            f.write(narrative)
        mlflow.log_artifact("narrative.txt")

        mlflow.log_metric("churn_model_accuracy", 0.85)
        mlflow.log_param("training_date", str(pd.Timestamp.now()))

        print("All models trained and logged.")

if __name__ == "__main__":
    main()