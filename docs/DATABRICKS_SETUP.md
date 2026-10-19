# Optional Databricks Setup

The same `src/streampulse/processing.py` PySpark code is designed to run on local Spark or an appropriately configured Databricks runtime. This repository does not include a Databricks job definition, workspace connector, or Delta Lake adapter; do not describe those as deployed.

1. Select a runtime compatible with Spark 3.5 and Python 3.11, or adapt/pin dependencies to the workspace runtime.
2. Install or import the package source and its dependencies in the workspace.
3. Grant the cluster/workload identity least-privilege access to the existing input bucket and output location.
4. Run `run_pipeline(bronze_path, gold_path)` from a job/notebook with a `SparkSession` available.
5. Verify schemas/counts and the saved `model_evaluation.json`; do not expose long-lived credentials in notebooks.

Delta Lake support is future work. The current pipeline reads and writes Parquet. No Databricks environment was configured or tested for this repository.