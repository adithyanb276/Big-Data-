# Setup and Local Run

## Requirements

- Python 3.11 (3.12 is not currently in the declared support range).
- Java 17 or 21 for PySpark 3.5.x.
- 4 GB available memory for the included small demonstration. Bigger workloads need more.
- No AWS account or credentials for local mode.

## Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

Set `JAVA_HOME` if Java is installed outside the standard system path. Confirm with `java -version` and `python -c 'import pyspark, pyarrow, duckdb; print(pyspark.__version__)'`.

## Full local pipeline

```bash
streampulse generate --events 10000 --users 10000 --movies 1000 --batch-size 5000 --seed 42 --output data/raw
for batch in data/raw/events-*.parquet; do streampulse ingest --source "$batch"; done
streampulse process --bronze data/bronze/events --gold data/gold --top-n 10
streamlit run app/streamlit_app.py
```

For a quick smoke dataset, reduce `--events` to 200 and `--users`/`--movies` to 30/20. `scripts/run_local.sh` wraps the sequence; set `EVENTS=200` for a small run. A running Spark ETL needs Java. Generation and ingestion can run without Java.

The event generator defaults to 10,000 users and 1,000 titles; event count is configurable up to multi-million scale. Parquet writes are bounded by `--batch-size`. `--malformed-rate` and `--missing-rate` can introduce invalid Bronze rows for quality checks.

## Tests and dashboard

Run `pytest -q`. Spark tests are skipped when Java is absent. Open the User portal for demo-user recommendations/history or Executive for analytics. Gold outputs are read through DuckDB; the app never trains ALS. The catalogue is deterministic demo metadata, not a licensed production catalogue.

## Configuration

`STREAMPULSE_MODE=local` is the default. `STREAMPULSE_DATA_DIR` controls the Bronze root and `STREAMPULSE_GOLD_DIR` the dashboard Gold path. Cloud mode additionally requires a pre-existing bucket configured with `STREAMPULSE_S3_BUCKET`, region, and AWS SDK credentials/role. S3 Bronze upload is implemented; a Gold-to-S3 serving connector is not. Do not place keys in source files or committed secrets. See [AWS_SETUP.md](AWS_SETUP.md) and [.env.example](../.env.example).

## Limits

The pipeline is explicit micro-batch processing; there is no continuous stream, scheduler, or end-to-end exactly-once guarantee. Bronze retries are content-addressed; Spark writes overwrite output datasets per run. Delta Lake is not implemented. Details: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).