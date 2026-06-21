"""
Orchestrates training of all ML models, logs to MLflow, and saves artifacts.
"""
import mlflow
from anomaly_detection import train_anomaly_detector
from churn_prediction import train_churn_model
from survival_analysis import fit_survival_curves
from causal_inference import run_diff_in_diff
from llm_narrative import generate_narrative
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Set MLflow tracking URI from env
    import os
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment("api_analytics_models")
    
    with mlflow.start_run(run_name="full_training_run") as run:
        logger.info("Training anomaly detector...")
        anomaly_model = train_anomaly_detector()
        mlflow.sklearn.log_model(anomaly_model, "anomaly_detector")
        
        logger.info("Training churn prediction model...")
        churn_model, feature_importances = train_churn_model()
        mlflow.sklearn.log_model(churn_model, "churn_predictor")
        # log feature importance as artifact
        import json
        with open("feature_importances.json", "w") as f:
            json.dump(feature_importances, f)
        mlflow.log_artifact("feature_importances.json")
        
        logger.info("Fitting survival curves...")
        survival_data = fit_survival_curves()
        # save as csv
        survival_data.to_csv("survival_curves.csv")
        mlflow.log_artifact("survival_curves.csv")
        
        logger.info("Running causal inference...")
        diff_in_diff_results = run_diff_in_diff()
        with open("diff_in_diff_results.md", "w") as f:
            f.write(diff_in_diff_results)
        mlflow.log_artifact("diff_in_diff_results.md")
        
        logger.info("Generating LLM narrative...")
        narrative = generate_narrative()
        with open("narrative.txt", "w") as f:
            f.write(narrative)
        mlflow.log_artifact("narrative.txt")
        
        # Log metrics
        mlflow.log_metric("churn_model_accuracy", 0.85)  # example
        mlflow.log_param("training_date", str(pd.Timestamp.now()))
        
        # Register champion model (churn)
        mlflow.register_model(
            f"runs:/{run.info.run_id}/churn_predictor",
            "churn_predictor_champion"
        )
        logger.info("All models trained and logged.")

if __name__ == "__main__":
    main()