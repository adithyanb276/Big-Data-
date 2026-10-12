# Architecture

Full write-up and diagram: `StreamPulse_Architecture_Plan.docx` and `StreamPulse_Architecture.svg`
(in the project root). This file is the quick reference for the repo.

## Pipeline (data flows top to bottom)

1. **Data Generation** (Fidal) — Python simulator; Zipfian title popularity; realistic sessions.
2. **Ingestion** (Fidal) — Boto3 micro-batch (~30–60s) → Snappy Parquet → S3.
3. **Bronze** (Fidal) — raw immutable Delta/Parquet in S3, partitioned `dt=YYYY-MM-DD/hr=HH`.
4. **Silver** (Lubaba) — PySpark on Databricks: dedupe, clean, sessionize, 5-min QoS windows.
5. **Gold** (Lubaba) — (a) ALS implicit-feedback recommender → top-N per user; (b) analytics tables.
6. **Serving** (Adithyan) — export Gold to Parquet, query with DuckDB, dual Streamlit portal (User + Executive) with Plotly, hosted on Streamlit Community Cloud.

**Cross-cutting:** Databricks Jobs orchestration · least-privilege IAM / secrets · frozen data contracts.

## Key decisions

- **Infra:** hybrid — AWS S3 (free tier) + Databricks Community Edition; MinIO + local PySpark fallback.
- **Processing model:** near-real-time **micro-batch** (honest framing of "real-time").
- **Storage:** **Delta Lake** across Bronze/Silver/Gold (ACID, schema enforcement, time travel).
- **Scale:** ~10k users × ~1k titles → several million events.
- **Recommender:** ALS implicit feedback, evaluated with ranking metrics (precision@k, NDCG).

## Decision log

- 2026-10-12 — reframed "real-time" as near-real-time micro-batch; chose hybrid infra; Delta across all layers. (initial plan)
- _add new design calls below as they happen_
