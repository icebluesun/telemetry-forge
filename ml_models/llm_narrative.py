"""
Generate executive summary using the Gemini API.
Falls back to a threshold-aware template if the API call fails.
"""
import os
import requests
import pandas as pd
from sqlalchemy import create_engine

# "-latest" alias always points at Google's newest model of this size
GEMINI_MODEL = os.getenv("GG_MODEL", "gemini-flash-lite-latest")
ERROR_WARN, ERROR_CRIT = 2.0, 5.0  # error-rate thresholds, %


def get_metrics():
    """Fetch latest-day metrics, day-over-day deltas and breakdowns from PostgreSQL."""
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        return None

    engine = create_engine(dsn, pool_pre_ping=True, pool_recycle=300)
    daily_query = """
    WITH days AS (
        SELECT DISTINCT event_date FROM stg_api_events ORDER BY event_date DESC LIMIT 2
    )
    SELECT
        event_date,
        COUNT(DISTINCT user_id) as dau,
        COUNT(*) as total_requests,
        ROUND(AVG(CASE WHEN is_error THEN 1.0 ELSE 0.0 END)::numeric * 100, 2) as error_rate,
        ROUND(AVG(latency_ms)::numeric, 1) as avg_latency,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 1) as p95_latency,
        ROUND(AVG(CASE WHEN rate_limited THEN 1.0 ELSE 0.0 END)::numeric * 100, 2) as rate_limited_pct,
        SUM(total_tokens) as total_tokens
    FROM stg_api_events
    WHERE event_date IN (SELECT event_date FROM days)
    GROUP BY event_date
    ORDER BY event_date DESC
    """
    breakdown_query = """
    WITH latest AS (SELECT MAX(event_date) as d FROM stg_api_events)
    SELECT {col} as name,
        COUNT(*) as requests,
        ROUND(AVG(CASE WHEN is_error THEN 1.0 ELSE 0.0 END)::numeric * 100, 2) as error_rate,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 1) as p95_latency
    FROM stg_api_events
    WHERE event_date = (SELECT d FROM latest)
    GROUP BY {col}
    ORDER BY error_rate DESC
    LIMIT 5
    """
    errors_query = """
    WITH latest AS (SELECT MAX(event_date) as d FROM stg_api_events)
    SELECT error_type, COUNT(*) as n
    FROM stg_api_events
    WHERE event_date = (SELECT d FROM latest) AND is_error AND error_type IS NOT NULL
    GROUP BY error_type ORDER BY n DESC LIMIT 5
    """
    with engine.connect() as conn:
        daily = pd.read_sql(daily_query, conn)
        if daily.empty:
            return None
        metrics = daily.iloc[0].to_dict()
        metrics["previous"] = daily.iloc[1].to_dict() if len(daily) > 1 else None
        for col in ("endpoint", "region", "user_tier"):
            metrics[f"by_{col}"] = pd.read_sql(breakdown_query.format(col=col), conn).to_dict("records")
        metrics["top_errors"] = pd.read_sql(errors_query, conn).to_dict("records")
        return metrics


def _status(error_rate):
    if error_rate >= ERROR_CRIT:
        return "critical"
    if error_rate >= ERROR_WARN:
        return "degraded"
    return "healthy"


def _build_prompt(m):
    def rows(records):
        return "\n".join(
            f"  - {r['name']}: {r['requests']} requests, {r['error_rate']}% errors, p95 {r['p95_latency']}ms"
            for r in records
        )

    prev = m["previous"]
    prev_text = (
        f"Previous day ({prev['event_date']}): DAU {prev['dau']}, {prev['total_requests']} requests, "
        f"{prev['error_rate']}% errors, avg latency {prev['avg_latency']}ms, p95 {prev['p95_latency']}ms."
        if prev else "No previous day available for comparison."
    )
    errors = ", ".join(f"{e['error_type']} ({e['n']})" for e in m["top_errors"]) or "none recorded"

    return f"""You are a site reliability lead writing the daily executive summary for an API platform.

Thresholds: error rate under {ERROR_WARN}% is healthy, {ERROR_WARN}-{ERROR_CRIT}% is degraded, above {ERROR_CRIT}% is critical.
Current status by error rate: {_status(m['error_rate'])}.

Latest day ({m['event_date']}): DAU {m['dau']}, {m['total_requests']} requests, {m['error_rate']}% errors,
avg latency {m['avg_latency']}ms, p95 {m['p95_latency']}ms, {m['rate_limited_pct']}% rate-limited, {m['total_tokens']} tokens.
{prev_text}

Top error types: {errors}

By endpoint (worst error rate first):
{rows(m['by_endpoint'])}

By region:
{rows(m['by_region'])}

By user tier:
{rows(m['by_user_tier'])}

Write 3-4 short paragraphs of plain prose (no headings, no bullet lists, no markdown):
1. Overall health verdict and the headline numbers, with day-over-day change.
2. Where problems are concentrated (endpoints, regions, tiers, error types) and what likely explains them.
3. Concrete recommended actions, most urgent first.
Be direct and specific; only cite numbers given above."""


def _fallback(m, reason):
    status = _status(m["error_rate"])
    verdict = {
        "healthy": "Platform is operating within normal parameters.",
        "degraded": f"Error rate is above the {ERROR_WARN}% warning threshold; investigation recommended.",
        "critical": f"Error rate is above the {ERROR_CRIT}% critical threshold; immediate attention required.",
    }[status]
    return f"""Platform Health Summary:
- DAU: {m['dau']:,}
- Requests: {m['total_requests']:,}
- Error Rate: {m['error_rate']:.2f}%
- Avg Latency: {m['avg_latency']:.1f}ms
- P95 Latency: {m['p95_latency']:.1f}ms
{verdict}

[source: template fallback, {reason}]"""


def generate_narrative():
    """Generate executive summary using Gemini."""

    metrics = get_metrics()
    if not metrics:
        return "Unable to fetch metrics from database."

    api_key = os.getenv("GG_API_TOKEN")
    if not api_key:
        return _fallback(metrics, "GG_API_TOKEN not set")

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": _build_prompt(metrics)}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.4},
    }

    try:
        response = requests.post(api_url, headers={"x-goog-api-key": api_key}, json=payload, timeout=60)
        print(f"[narrative] Gemini status={response.status_code} body={response.text[:200]!r}")

        if response.status_code != 200:
            return _fallback(metrics, f"Gemini status {response.status_code}")

        result = response.json()
        parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            return _fallback(metrics, "Gemini empty output")
        model_version = result.get("modelVersion", GEMINI_MODEL)
        return f"Platform Health Summary:\n\n{text}\n\n[source: LLM {model_version}]"

    except Exception as e:
        print(f"[narrative] exception: {e!r}")
        return _fallback(metrics, f"error: {type(e).__name__}")


if __name__ == "__main__":
    print(generate_narrative())
