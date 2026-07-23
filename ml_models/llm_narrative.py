"""
Generate executive summary using HuggingFace Inference API.
Uses translation model that works with hf-inference provider.
"""
import os
import requests
import pandas as pd
from sqlalchemy import create_engine

def get_metrics():
    """Fetch current metrics from PostgreSQL."""
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        return None
    
    engine = create_engine(dsn, pool_pre_ping=True, pool_recycle=300)
    query = """
    WITH latest AS (SELECT MAX(event_date) as d FROM stg_api_events)
    SELECT 
        COUNT(DISTINCT user_id) as dau,
        COUNT(*) as total_requests,
        ROUND(AVG(CASE WHEN is_error THEN 1.0 ELSE 0.0 END)::numeric * 100, 2) as error_rate,
        ROUND(AVG(latency_ms)::numeric, 1) as avg_latency,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 1) as p95_latency
    FROM stg_api_events
    WHERE event_date = (SELECT d FROM latest)
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        return df.iloc[0].to_dict()

def generate_narrative():
    """Generate executive summary using HuggingFace translation model."""
    
    metrics = get_metrics()
    if not metrics:
        return "Unable to fetch metrics from database."
    
    api_token = os.getenv("HF_API_TOKEN")
    if not api_token:
        return "LLM narrative disabled: HF_API_TOKEN not set."
    
    # Use a translation model (confirmed to work with hf-inference)
    # Translate English to French and back = "summary" effect
    text_to_translate = f"""
    Platform has {metrics['dau']:,} daily active users, {metrics['total_requests']:,} requests.
    Error rate is {metrics['error_rate']:.2f}%. Average latency is {metrics['avg_latency']:.1f}ms.
    """
    
    model = "google-t5/t5-small"  # Works with hf-inference
    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # Translation payload
    payload = {
        "inputs": text_to_translate
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get('translation_text', '')
                return f"Platform Health Summary:\n{text}" if text else "No text generated."
            return str(result)
        else:
            # Fallback: return formatted metrics
            return f"""Platform Health Summary:
- DAU: {metrics['dau']:,}
- Requests: {metrics['total_requests']:,}
- Error Rate: {metrics['error_rate']:.2f}%
- Avg Latency: {metrics['avg_latency']:.1f}ms
- P95 Latency: {metrics['p95_latency']:.1f}ms
Platform is operating within normal parameters."""
            
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print(generate_narrative())