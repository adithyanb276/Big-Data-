# Work Plan — Checklists & Schedule

Tick boxes as you go. This is the single "what do I do next" file.

## Fidal — Cloud Data Engineering & Ingestion

- [ ] Build Python telemetry simulator (Zipfian popularity, realistic sessions, tunable scale)
- [ ] Create AWS S3 bucket + least-privilege IAM user
- [ ] Boto3 uploader: batch → Snappy Parquet → S3, idempotent + retry
- [ ] Bronze Delta layer with `dt/hr` partitioning + schema enforcement
- [ ] Data-quality checks (nulls, bad types, duplicates)
- [ ] Databricks Jobs schedule for the micro-batch refresh (shared concern)
- [ ] **Freeze Contract A** and commit sample data to `data/samples/`
- **Learn:** cloud object storage, Delta Lake, partitioning, idempotent pipelines, orchestration

## Lubaba — Big Data Processing & ML

- [ ] Set up Databricks Community Edition + S3 connection (shared concern; lead the Spark pairing)
- [ ] Silver PySpark ETL: dedupe, null handling, sessionization
- [ ] 5-minute tumbling-window QoS metrics
- [ ] Build implicit-feedback rating matrix from watch-completion
- [ ] Train ALS; tune `rank / regParam / alpha / maxIter`
- [ ] Evaluate with ranking metrics (precision@k, NDCG); add popularity cold-start fallback
- [ ] Write Gold `recommendations` + analytics tables; **freeze Contract B**
- **Learn:** distributed Spark, Medallion pattern, matrix-factorization recommenders, implicit feedback, ranking evaluation

## Adithyan — Analytics Engineering & Serving

- [ ] Streamlit skeleton + dual-portal wireframes
- [ ] DuckDB serving layer over Gold Parquet (build against mocked Contract B first)
- [ ] Executive Portal: QoS, completion-funnel, device, churn-risk dashboards (Plotly)
- [ ] User Portal: personalized slates, "why recommended", continue-watching
- [ ] Recommender-quality visualization (how good are the recs?)
- [ ] Deploy to Streamlit Community Cloud (secrets, not committed keys)
- [ ] Final repository documentation / README polish (shared concern)
- **Learn:** analytics engineering (DuckDB over Parquet), data viz & dashboards, recommender consumption, cloud deployment

## 3-Week schedule

| Phase | Fidal | Lubaba | Adithyan |
|---|---|---|---|
| **Week 1** (Days 1–7) | Simulator; S3 + IAM; first Bronze uploads; freeze Contract A | Databricks CE; design Silver vs Contract A; prototype S3 reads | Streamlit skeleton + wireframes; DuckDB layer vs mocked Gold |
| **Week 2** (Days 8–14) | Harden ingestion; data-quality; Databricks Jobs schedule | Silver ETL + QoS; rating matrix; train & tune ALS; lead Spark pairing | Wire portals to real Gold; Plotly dashboards; rec-quality viz |
| **Week 3** (Days 15–21) | Full-volume run; cost/limit checks; validate MinIO fallback | Final ALS eval; freeze Gold; model write-up | Deploy to Streamlit Cloud; polish; integration test; final docs |

## Shared-learning guarantee

All three pair on the Databricks + Spark setup in Week 2, so **everyone writes at least one Spark job** regardless of their primary module.
