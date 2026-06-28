"""
Synthetic API telemetry generator – simulates realistic LLM-as-a-service platform events.
Distributions mirror real-world usage: Pareto user activity, latency by endpoint,
correlated errors with load spikes, and varied tier behaviours.
"""
import random
import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import numpy as np
from faker import Faker

fake = Faker()

# Configuration constants
ENDPOINTS = ["/v1/completions", "/v1/chat", "/v1/embeddings", "/v1/classify"]
MODEL_VARIANTS = ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "gpt-4", "gpt-3.5"]
USER_TIERS = ["free", "pro", "enterprise"]
REGIONS = ["us-east", "us-west", "eu-west", "ap-southeast"]
SDK_VERSIONS = ["1.2.3", "1.2.4", "1.3.0", "2.0.0"]
ERROR_TYPES = [None, "RateLimitError", "AuthenticationError", "InvalidRequestError",
               "APIError", "TimeoutError", "InternalServerError"]

# Latency distributions per endpoint (ms) – lognormal fits real systems
LATENCY_PARAMS = {
    "/v1/completions": (5.0, 1.2),
    "/v1/chat": (5.5, 1.5),
    "/v1/embeddings": (4.0, 0.8),
    "/v1/classify": (3.5, 0.9)
}

# Token counts: input ~ lognormal, output ~ exponential with endpoint bias
TOKEN_INPUT_MEAN = 500
TOKEN_OUTPUT_BASE = 200


class APITelemetryGenerator:
    """Generates batches of API events with realistic distributions."""
    
    def __init__(self, seed: int = 42, churn_rate: float = 0.15):
        self.seed = seed
        self.churn_rate = churn_rate  # 15% of users will churn
        random.seed(seed)
        np.random.seed(seed)
        # Pre-generate a fixed pool of users to simulate cohorts
        self.user_pool = [self._create_user() for _ in range(1000)]
        self.user_weights = self._compute_pareto_weights()
        self.event_counter = 0

    def _create_user(self) -> Dict[str, Any]:
        will_churn = random.random() < self.churn_rate
        churn_day = random.randint(30, 90) if will_churn else None
        
        return {
            "user_id": str(uuid.uuid4()),
            "tier": random.choices(USER_TIERS, weights=[0.7, 0.2, 0.1])[0],
            "region": random.choice(REGIONS),
            "cohort_date": fake.date_time_between(start_date="-180d", end_date="-1d").replace(tzinfo=timezone.utc),
            "will_churn": will_churn,
            "churn_day": churn_day,
            "active_days": 0
        }

    def _compute_pareto_weights(self) -> List[float]:
        """Pareto distribution (80/20) for user activity."""
        ranks = np.arange(1, len(self.user_pool)+1)
        weights = 1.0 / np.power(ranks, 1.2)
        return weights / weights.sum()

    def is_user_active(self, user: Dict[str, Any], days_since_cohort: int) -> bool:
        """Check if user is still active on a given day."""
        if not user.get("will_churn", False):
            return True
        churn_day = user.get("churn_day")
        if churn_day is None:
            return True
        return days_since_cohort < churn_day

    def generate_event(self, base_time: datetime, user: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a single realistic API event."""
        # Select user (with Pareto weighting) if not provided
        if user is None:
            user = np.random.choice(self.user_pool, p=self.user_weights)
        user_tier = user["tier"]
        
        # Endpoint and model
        endpoint = random.choices(
            ENDPOINTS,
            weights=[0.4, 0.3, 0.2, 0.1]
        )[0]
        model = random.choice(MODEL_VARIANTS)
        
        # Tokens
        input_tokens = int(np.random.lognormal(mean=np.log(TOKEN_INPUT_MEAN), sigma=1.0))
        output_tokens = int(np.random.exponential(scale=TOKEN_OUTPUT_BASE) + 50)
        output_tokens = max(1, output_tokens)
        
        # Latency depends on endpoint and token count
        base_mean, base_sigma = LATENCY_PARAMS[endpoint]
        token_factor = 1 + (input_tokens + output_tokens) / 2000.0
        latency = np.random.lognormal(mean=np.log(base_mean * token_factor), sigma=base_sigma)
        latency = max(10, latency)
        
        # INJECT ANOMALIES (2% of events)
        if random.random() < 0.02:
            latency = latency * random.uniform(5, 20)  # 5x-20x spike
            status_code = random.choices([500, 503, 504, 429], weights=[0.4, 0.3, 0.2, 0.1])[0]
            error_type = random.choice(["InternalServerError", "TimeoutError", "RateLimitError"])
            rate_limited = (status_code == 429)
        else:
            # Normal error patterns
            load_factor = min(1.0, (self.event_counter % 1000) / 500.0)
            base_error_rate = 0.05
            error_rate = base_error_rate + 0.2 * load_factor
            has_error = random.random() < error_rate
            status_code = 200 if not has_error else random.choices(
                [429, 401, 400, 500, 504, 503],
                weights=[0.4, 0.2, 0.2, 0.1, 0.05, 0.05]
            )[0]
            error_type = None if not has_error else random.choice(
                [e for e in ERROR_TYPES if e is not None]
            )
            rate_limited = (status_code == 429) or (error_type == "RateLimitError")
        
        # SDK and region from user
        sdk_version = random.choice(SDK_VERSIONS)
        region = user["region"]
        
        # Session: sometimes new, sometimes existing
        session_id = str(uuid.uuid4()) if random.random() < 0.3 else fake.uuid4()
        
        # Timestamp: add jitter around base_time
        timestamp = base_time + timedelta(milliseconds=random.randint(0, 1000))
        
        return {
            "event_id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "user_id": user["user_id"],
            "user_tier": user_tier,
            "endpoint": endpoint,
            "model_variant": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(latency, 1),
            "status_code": status_code,
            "error_type": error_type,
            "sdk_version": sdk_version,
            "region": region,
            "session_id": session_id,
            "rate_limited": rate_limited,
            "will_churn": user["will_churn"],
            "churn_day": user["churn_day"]
        }

    def generate_batch(self, count: int, start_time: datetime) -> List[Dict[str, Any]]:
        """Generate a batch of events starting from start_time, with sequential timestamps."""
        events = []
        base = start_time
        
        for i in range(count):
            # Select a random user
            user = np.random.choice(self.user_pool, p=self.user_weights)
            
            # Check if user is active at this time
            days_since_cohort = (base - user["cohort_date"]).days
            if not self.is_user_active(user, days_since_cohort):
                # User has churned, skip this event
                continue
            
            # Advance time by a few ms to simulate real stream
            if i % 10 == 0:
                base += timedelta(milliseconds=random.randint(1, 50))
            
            event = self.generate_event(base, user)
            
            # Override timestamp with incremental time to simulate streaming
            if events:
                prev_ts = datetime.fromisoformat(events[-1]["timestamp"])
                new_ts = max(prev_ts + timedelta(milliseconds=1), datetime.fromisoformat(event["timestamp"]))
                event["timestamp"] = new_ts.isoformat()
            
            events.append(event)
            self.event_counter += 1
        
        return events


if __name__ == "__main__":
    # Quick test
    gen = APITelemetryGenerator()
    now = datetime.now(timezone.utc)
    batch = gen.generate_batch(10, now)
    print(json.dumps(batch, indent=2))