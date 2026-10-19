# Three-Week Team Workplan

The original checklist and schedule remain in [../WORKPLAN.md](../WORKPLAN.md). This status reflects repository work as of 2026-10-19.

| Week | Fidal: Ingestion | Lubaba: Processing and ML | Adithyan: Serving |
|---|---|---|---|
| 1 | Simulator, schema, local/S3 Bronze | Spark setup, Silver contract | DuckDB foundation, portal structure |
| 2 | Retry/idempotency, data quality | Session/QoS, ALS, ranking evaluation | Portal charts and recommendation rendering |
| 3 | Cloud test, cost review | Full local run, model report | Deployment, polish, integration review |

Implemented in source: synthetic generation, local/S3 Parquet ingestion, Spark transformation/ALS code, DuckDB layer, both portal views, and docs. The Python tests passed in the implementation environment; Spark tests were skipped because Java was absent. Cloud, Databricks, and deployment require team-owned environments and remain unchecked. Do not treat cloud checklist work as complete until a service-backed test is recorded.