from sklearn.ensemble import IsolationForest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os

def load_latency_error_ts():
    """Load time-series aggregated data from PostgreSQL."""
    dsn = os.getenv("POSTGRES_DSN")
    engine = create_engine(dsn)
    query = """
    SELECT event_date, 
           avg(latency_ms) as avg_latency,
           count(case when is_error then 1 end) as error_count,
           count(*) as total_requests
    FROM stg_api_events
    GROUP BY event_date
    ORDER BY event_date
    """
    df = pd.read_sql(query, engine)
    df['error_rate'] = df['error_count'] / df['total_requests']
    return df

def train_anomaly_detector():
    df = load_latency_error_ts()
    # Features: moving averages, deviations
    df['latency_ma7'] = df['avg_latency'].rolling(7).mean()
    df['error_ma7'] = df['error_rate'].rolling(7).mean()
    df['latency_std7'] = df['avg_latency'].rolling(7).std()
    df['error_std7'] = df['error_rate'].rolling(7).std()
    df = df.dropna()
    features = ['avg_latency', 'error_rate', 'latency_ma7', 'error_ma7', 
                'latency_std7', 'error_std7']
    X = df[features].values
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X)
    return model