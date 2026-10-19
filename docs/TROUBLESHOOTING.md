# Troubleshooting and Verification Status

- **`JAVA_GATEWAY_EXITED` / `java` missing:** install Java 17 or 21, set `JAVA_HOME`, restart the shell, and check `java -version`. Spark integration tests skip when Java is unavailable.
- **Python dependency mismatch:** use Python 3.11 in a fresh `.venv`, then install `requirements.txt`; avoid running under a different interpreter from the one where dependencies were installed.
- **No Bronze input:** generate Parquet and ingest every `events-*.parquet` file before invoking `process`.
- **Empty dashboard:** verify `data/gold` exists and contains Parquet datasets. Neither FastAPI nor React launches Spark or generates recommendations.
- **S3 authorization or missing bucket:** cloud mode requires a pre-provisioned private bucket, correct role/region, and scoped permissions. Local mode is independent of AWS.
- **ALS no recommendations:** check non-empty interactions and integer user/item identifiers. Sparse users are eligible for popularity fallback.
- **Large jobs:** reduce event count or batch size for memory pressure; Spark and ALS still require sufficient JVM heap and driver memory.

## Verification from the implementation environment

Verified: deterministic generation, Snappy Parquet reads, local content-addressed/date-hour Bronze ingestion and repeat-delivery behavior, DuckDB Parquet scans and parameterized filters, FastAPI endpoint/response/filter/fallback tests, browser requests through the Vite `/api` proxy, Python module compilation, and the Vite production build. The available full Python suite passed with Spark-specific tests skipped.

Not verified: PySpark transformations and ALS training (no Java executable was present), live S3 (no configured credentials/bucket), Databricks (no workspace), persistent Gold-data deployment/sync, or Vercel/Render deployment. The browser was exercised against honest empty Gold state; there are no processed sample Gold outputs in this environment, so populated chart content remains unverified.