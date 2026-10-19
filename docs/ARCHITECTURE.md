# StreamPulse Architecture

The repository's original architecture record is maintained at [../ARCHITECTURE.md](../ARCHITECTURE.md). This implementation uses local-first micro-batches; local/S3 Parquet Bronze is processed by PySpark into Silver and Gold Parquet. Spark MLlib ALS trains and evaluates recommendations as an explicit batch operation. DuckDB queries exported Gold datasets for the Streamlit User and Executive portals.

```mermaid
flowchart LR
    G[Generator] --> P[Snappy Parquet]
    P --> I[Local or optional S3 ingestion]
    I --> B[Bronze date/hour partitions]
    B --> S[PySpark Silver validation and sessions]
    S --> M[ALS and held-out ranking evaluation]
    S --> A[Gold analytics]
    M --> O[Gold Parquet]
    A --> O
    O --> D[DuckDB]
    D --> U[User portal]
    D --> E[Executive portal]
```

Delta Lake, continuous streaming, managed orchestration, and cloud deployment are not implemented or verified. Cloud mode does not create resources. Refer to [AWS setup](AWS_SETUP.md) and [Databricks setup](DATABRICKS_SETUP.md) for the current boundary.