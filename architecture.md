ARCHITECTURE.md - Text Version
================================

TELEMETRYFORGE - ARCHITECTURE DEEP DIVE

OVERVIEW
--------
Complete API analytics platform demonstrating modern data engineering.
All free tier services. Zero maintenance.

DATA FLOW
---------
1. GitHub Actions (daily cron)
   ↓
2. Synthetic Data Generation (generator.py)
   - Pareto user activity
   - Lognormal latency per endpoint
   - Errors correlated with load
   - Tokens, regions, SDK versions
   ↓
3. Kafka Streaming (Aiven)
   - 1 event every 10 seconds
   - 90 days historical
   - SASL/SSL auth
   ↓
4. PostgreSQL Storage (Aiven)
   - Idempotent inserts
   - Auto-cull: last 90 days only
   - Always under 1GB
   ↓
5. dbt Transformation
   - Staging: clean, rename
   - Marts: DAU, endpoints, errors, cohorts, tokens
   - Tests: not_null, unique, accepted_values
   ↓
6. ML Models
   - Anomaly: Isolation Forest
   - Churn: Gradient Boosting
   - Survival: Kaplan-Meier
   - Causal: Diff-in-Diff
   - Narrative: HuggingFace LLM
   - All logged to MLflow (DagsHub)
   ↓
7. Dashboard (Streamlit on HuggingFace)
   - 8 tabs
   - Reads PostgreSQL
   - Auto-refresh daily

TECHNOLOGY DECISIONS
--------------------
Kafka (Aiven)        - Industry standard, free tier
PostgreSQL (Aiven)   - SQL, free tier, dbt native
dbt                  - Modular, tests, docs, lineage
GitHub Actions       - Free, cron, integrated
MLflow (DagsHub)     - Free UI, model registry
Streamlit (HF)       - Free hosting, public URL
Great Expectations   - Automated data quality

FREE TIER LIMITS
----------------
Aiven PostgreSQL: 1GB  → 270MB used
Aiven Kafka: 250kb/s   → Well under
GitHub Actions: 2000min/month → ~30min used
HuggingFace: 2 vCPU, 16GB → Under
DagsHub: Unlimited public → Free

DATA RETENTION
--------------
New events daily
Keep last 90 days
Auto-delete older
Always ~270MB
Never exceeds 1GB

SECURITY
--------
Kafka: SASL/SSL + SCRAM
PostgreSQL: SSL + password
GitHub: Secrets + env vars
Dashboard: Public (read-only)

WHAT THIS DEMONSTRATES
----------------------
- Data Engineering: Kafka, PostgreSQL, dbt
- ML Engineering: Multiple models, experiment tracking
- Data Science: Survival, causal inference
- Software Engineering: Clean code, tests, docs
- DevOps: CI/CD, orchestration, hosting
- Architecture: Streaming, batch, microservices

ALTERNATIVES REJECTED
---------------------
Airflow        → Overkill
Snowflake      → Not free
Kubernetes     → Too complex
Self-hosted    → Maintenance overhead

SUMMARY
-------
Complete production-grade analytics platform that:
- Runs forever on free tier
- Demonstrates full data + ML stack
- Requires zero maintenance
- Shows real engineering skills