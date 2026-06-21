import pandas as pd
from lifelines import KaplanMeierFitter
import os
from sqlalchemy import create_engine

def fit_survival_curves():
    dsn = os.getenv("POSTGRES_DSN")
    engine = create_engine(dsn)
    query = """
    WITH user_lifetimes AS (
        SELECT user_id,
               user_tier,
               min(event_date) as acquisition_date,
               max(event_date) as last_active,
               CASE WHEN max(event_date) >= (CURRENT_DATE - interval '30 days') THEN 0 ELSE 1 END as churned,
               (max(event_date) - min(event_date)) + 1 as lifetime_days
        FROM stg_api_events
        GROUP BY user_id, user_tier
    )
    SELECT * FROM user_lifetimes
    """
    df = pd.read_sql(query, engine)
    
    # Convert lifetime_days to numeric
    if df['lifetime_days'].dtype == 'object':
        df['lifetime_days'] = df['lifetime_days'].dt.days
    else:
        df['lifetime_days'] = pd.to_numeric(df['lifetime_days'], errors='coerce')
    
    df = df.dropna(subset=['lifetime_days'])
    
    # Fit Kaplan-Meier per tier
    kmf_by_tier = {}
    for tier in df['user_tier'].unique():
        sub = df[df['user_tier'] == tier]
        if len(sub) > 1:
            kmf = KaplanMeierFitter()
            kmf.fit(sub['lifetime_days'], event_observed=(1 - sub['churned']))
            kmf_by_tier[tier] = kmf
    
    # Return survival data for saving
    survival_data = pd.DataFrame()
    for tier, kmf in kmf_by_tier.items():
        temp = pd.DataFrame({
            'timeline': kmf.timeline,
            'survival_prob': kmf.survival_function_.values.flatten(),
            'tier': tier
        })
        survival_data = pd.concat([survival_data, temp])
    return survival_data