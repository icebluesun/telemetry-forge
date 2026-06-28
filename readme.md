---
title: Telemetry Forge
emoji: 📊
colorFrom: indigo
colorTo: yellow
sdk: docker
pinned: false
license: mit
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference


# TelemetryForge

**Live API analytics platform with streaming, dbt, ML, and dashboard.**

[![Pipeline Status](https://github.com/yourusername/telemetry-forge/actions/workflows/pipeline.yml/badge.svg)](https://github.com/yourusername/telemetry-forge/actions)

---

## What It Does

Generates realistic API telemetry (like OpenAI/Claude usage), streams through Kafka, stores in PostgreSQL, transforms with dbt, trains ML models, and displays on a live dashboard.

---

## Live Demo

[https://huggingface.co/spaces/yourusername/telemetry-forge](https://huggingface.co/spaces/yourusername/telemetry-forge)

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Streaming | Kafka (Aiven) |
| Storage | PostgreSQL (Aiven) |
| Transformation | dbt |
| Orchestration | GitHub Actions |
| ML Tracking | MLflow (DagsHub) |
| Dashboard | Streamlit (HuggingFace) |
| Data Quality | Great Expectations |

---

## Skills Demonstrated

Python · SQL · dbt · Kafka · PostgreSQL · GitHub Actions · MLflow · Great Expectations · Streamlit · Scikit-learn · Survival Analysis · Causal Inference · LLM Integration

---

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/telemetry-forge.git
cd telemetry-forge

# Set env vars
export POSTGRES_DSN="postgresql://..."
export KAFKA_BROKERS="..."
export KAFKA_USERNAME="..."
export KAFKA_PASSWORD="..."
export KAFKA_TOPIC="api_events"

# Install
pip install -r global_requirements.txt

# Generate 90 days of data
cd data_generation
python producer.py

# Ingest
cd ../ingestion
python consumer.py

# Run dbt
cd ../dbt
dbt run --profiles-dir .

# Train ML
cd ../ml_models
python train_all.py

# Dashboard
cd ../dashboard
streamlit run app.py