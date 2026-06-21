
# Causal Inference: Impact of Latency Improvement Rollout on Developer Retention

## Background
On 2025-01-15, we rolled out a latency optimization for the `/v1/completions` endpoint, targeting enterprise-tier users in the us-east region. This improvement reduced p95 latency by ~30%.

## Design
We used a difference-in-differences approach comparing:
- **Treatment group**: Enterprise users in us-east
- **Control group**: Enterprise users in us-west and pro/free users in us-east

## Data
We aggregated daily active users and token consumption from 2024-12-01 to 2025-02-28.

## Results
- **Retention effect**: The treatment group showed a 12% relative increase in 7-day retention post-rollout compared to controls (p < 0.01).
- **Token volume**: Average daily tokens per user increased by 8% in treatment group, suggesting higher engagement.

## Conclusion
The latency improvement positively impacted developer retention and engagement, supporting further investments in performance optimization.
    