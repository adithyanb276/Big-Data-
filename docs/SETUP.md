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
cd frontend
npm install
cp .env.example .env.local
cd ..
```

Set `JAVA_HOME` if Java is installed outside the standard system path. Confirm with `java -version` and `python -c 'import pyspark, pyarrow, duckdb; print(pyspark.__version__)'`.

## Full local pipeline

```bash
streampulse generate --events 10000 --users 10000 --movies 1000 --batch-size 5000 --seed 42 --output data/raw
for batch in data/raw/events-*.parquet; do streampulse ingest --source "$batch"; done
streampulse process --bronze data/bronze/events --gold data/gold --top-n 10
uvicorn app.main:app --reload --port 8000
# In another terminal:
cd frontend && npm run dev
```

For a quick smoke dataset, reduce `--events` to 200 and `--users`/`--movies` to 30/20. `scripts/run_local.sh` wraps generation, ingestion, and Spark processing; set `EVENTS=200` for a small run. A running Spark ETL needs Java. Generation and ingestion can run without Java.

The event generator defaults to 10,000 users and 1,000 titles; event count is configurable up to multi-million scale. Parquet writes are bounded by `--batch-size`. `--malformed-rate` and `--missing-rate` can introduce invalid Bronze rows for quality checks.

## Tests and dashboard

Run `pytest -q`; Spark tests skip when Java is absent. Build the client with `cd frontend && npm run build`. Open `http://localhost:5173`; it calls FastAPI on port 8000. Gold outputs are read through DuckDB; the API never starts Spark or trains ALS. If a user's slate is absent but title-view analytics exist, the API returns a popularity fallback labeled `popularity_fallback`. The catalogue is deterministic demo metadata, not a licensed production catalogue.

## Configuration

`STREAMPULSE_MODE=local` is the default. `STREAMPULSE_DATA_DIR` controls the Bronze root and `STREAMPULSE_GOLD_DIR` the API Gold path. `STREAMPULSE_CORS_ORIGINS` is a comma-separated origin allowlist and `PORT` sets the deployed backend port. Set frontend `VITE_API_BASE_URL` to the deployed API URL; local Vite proxies `/api` to port 8000. Cloud mode requires a pre-existing bucket and AWS SDK credentials/role. The API currently reads local Gold Parquet; an operator must provision or sync Gold data to persistent backend storage. See [AWS_SETUP.md](AWS_SETUP.md), [DEPLOYMENT.md](DEPLOYMENT.md), and [.env.example](../.env.example).

API routes and response contracts: [API.md](API.md).

## Limits

The pipeline is explicit micro-batch processing; there is no continuous stream, scheduler, or end-to-end exactly-once guarantee. Bronze retries are content-addressed; Spark writes overwrite output datasets per run. Delta Lake is not implemented. Details: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).