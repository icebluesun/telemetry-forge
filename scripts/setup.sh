#!/bin/bash
echo "Setting up API Analytics Platform..."

# Check for required env vars
if [ -z "$KAFKA_BROKERS" ] || [ -z "$POSTGRES_DSN" ]; then
  echo "Error: Please set KAFKA_BROKERS and POSTGRES_DSN"
  exit 1
fi

# Install Python dependencies
pip install -r global_requirements.txt

# Initialize dbt
cd dbt
dbt deps
dbt debug --profiles-dir .
cd ..

# Initialize Great Expectations
great_expectations --v3-api init

# MLflow
export MLFLOW_TRACKING_URI=https://dagshub.com/yourusername/telemetry-forge.mlflow

# Dashboard
huggingface-cli login --token $HF_API_TOKEN

echo "Setup complete!"