---
title: TelemetryForge
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.58.0
app_file: app.py
pinned: false
license: mit
---

# TelemetryForge

**Live API analytics platform — streaming, dbt, ML models, and a real-time dashboard.**

[![Pipeline](https://github.com/icebluesun/telemetry-forge/actions/workflows/main.yml/badge.svg)](https://github.com/icebluesun/telemetry-forge/actions/workflows/main.yml)
[![MLflow on DagsHub](https://img.shields.io/badge/MLflow-DagsHub-orange?logo=mlflow)](https://dagshub.com/dennis13/telemetry-forge.mlflow)
[![HuggingFace Space](https://img.shields.io/badge/Dashboard-HuggingFace-yellow?logo=huggingface)](https://huggingface.co/spaces/icebluesun/telemetry-forge)

---

## What It Does

Generates realistic API telemetry (modelled after OpenAI/Claude usage patterns), streams through Kafka, stores in PostgreSQL, transforms with dbt, trains ML models, and displays everything on a live Streamlit dashboard — all running automatically every day via GitHub Actions.

---

## Live Links

| | |
|---|---|
| 📊 Dashboard | https://icebluesun-telemetry-forge.hf.space |
| 🧪 MLflow Experiments | https://dagshub.com/dennis13/telemetry-forge.mlflow |
| ⚙️ Pipeline Runs | https://github.com/icebluesun/telemetry-forge/actions |

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Streaming | Kafka (Aiven) |
| Storage | PostgreSQL (Aiven) |
| Transformation | dbt |
| Orchestration | GitHub Actions |
| ML Tracking | MLflow (DagsHub) |
| Dashboard | Streamlit (HuggingFace Spaces) |
| Data Quality | Great Expectations |

---

## ML Models

| Model | Purpose |
|-------|---------|
| Isolation Forest | Anomaly detection on latency + error rates |
| Random Forest | Churn prediction |
| Kaplan-Meier | Survival analysis by user tier |
| Diff-in-Diff | Causal inference on feature rollouts |
| T5 (HF Inference) | LLM-generated executive narrative |

---

## Skills Demonstrated

Python · SQL · dbt · Kafka · PostgreSQL · GitHub Actions · MLflow · Great Expectations · Streamlit · Scikit-learn · Survival Analysis · Causal Inference · LLM Integration

---

## Quick Start

```bash
git clone https://github.com/icebluesun/telemetry-forge.git
cd telemetry-forge

# Copy and fill in your credentials
cp .env.example .env

# Install dependencies
pip install -r global_requirements.txt

# Run local pipeline test
python test_pipeline_local.py
```
