# StreamPulse

Cloud-native video-viewing analytics & personalization platform.
Big Data Technologies & Cloud Computing capstone · 3 members · 3-week build.

Synthetic viewing telemetry → local/S3 Bronze Parquet → PySpark Silver/Gold and Spark MLlib ALS
→ DuckDB over Gold Parquet → FastAPI REST API → React + Vite dashboard.

## Team & ownership

| Member | Workstream | Folder |
|---|---|---|
| **Fidal** | Cloud data engineering & ingestion | `src/streampulse/generator.py`, `ingestion.py` |
| **Lubaba** | Big data processing & ML | `src/streampulse/processing.py` |
| **Adithyan** | Analytics engineering & serving | `src/streampulse/serving.py`, `app/` |

## Repo layout

Implementation lives under `src/streampulse/`; team ownership remains split by component.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the working flow and [docs/CONTRACTS.md](docs/CONTRACTS.md) for the event and Gold schemas.

## Quick start

Requirements: Python 3.11, Node 20+, and Java 17+ for Spark. Local mode requires no AWS credentials.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
cd frontend && npm ci && cd ..
streampulse generate --events 10000 --users 10000 --movies 1000 --batch-size 5000 --seed 42 --output data/raw
for batch in data/raw/events-*.parquet; do streampulse ingest --source "$batch"; done
streampulse process --bronze data/bronze/events --gold data/gold
uvicorn app.main:app --reload --port 8000
```

In a second terminal, run `cd frontend && cp .env.example .env.local && npm run dev`, then open `http://localhost:5173`. The blank local API URL uses the Vite `/api` proxy. For a Spark-free frontend/API smoke test, point `STREAMPULSE_GOLD_DIR` at Gold Parquet fixtures. Run `pytest -q`; build with `cd frontend && npm run build`.

## Status

Implemented: generator, Parquet, local/S3 ingestion code, PySpark Silver/Gold and ALS, DuckDB serving, FastAPI endpoints, and a React dashboard. FastAPI tests and the Vite production build are verified. Spark requires Java; the available environment has no JVM, so Spark/ALS execution was not verified. AWS and Databricks were not configured or cloud-tested. Separate deployment is documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md); see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for verification details.
