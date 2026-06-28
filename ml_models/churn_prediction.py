import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
import os
from sqlalchemy import create_engine
import numpy as np

def load_user_features():
    dsn = os.getenv("POSTGRES_DSN")
    engine = create_engine(dsn)
    query = """
    WITH user_activity AS (
        SELECT 
            user_id,
            max(event_date) as last_active,
            count(*) as total_requests,
            avg(latency_ms) as avg_latency,
            sum(case when is_error then 1 else 0 end) as error_count,
            count(distinct event_date) as active_days,
            sum(total_tokens) as total_tokens,
            max(churn_day) as churn_day
        FROM stg_api_events
        GROUP BY user_id
    ),
    user_tier AS (
        SELECT DISTINCT ON (user_id) user_id, user_tier
        FROM stg_api_events
        ORDER BY user_id, event_date DESC
    )
    SELECT 
        ua.*, 
        ut.user_tier,
        CURRENT_DATE - ua.last_active as days_since_last,
        CASE 
            WHEN ua.churn_day IS NOT NULL 
            AND (CURRENT_DATE - ua.last_active) > ua.churn_day 
            THEN 1 
            ELSE 0 
        END as churned
    FROM user_activity ua
    LEFT JOIN user_tier ut ON ua.user_id = ut.user_id
    """
    df = pd.read_sql(query, engine)
    
    # Ensure at least some churn exists
    if df['churned'].sum() == 0:
        print("⚠️ No churn detected. Adding synthetic churn for demo.")
        np.random.seed(42)
        df.loc[np.random.choice(df.index, size=int(len(df)*0.1), replace=False), 'churned'] = 1
    
    return df

def train_churn_model():
    df = load_user_features()
    
    feature_cols = ['total_requests', 'avg_latency', 'error_count', 'active_days',
                    'total_tokens', 'days_since_last']
    X = df[feature_cols].fillna(0)
    y = df['churned']
    
    tier_dummies = pd.get_dummies(df['user_tier'], prefix='tier')
    X = pd.concat([X, tier_dummies], axis=1)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:,1])
    print(f"Churn model accuracy: {acc:.3f}, AUC: {auc:.3f}")
    
    importances = dict(zip(X.columns, model.feature_importances_))
    return model, importances