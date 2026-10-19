# StreamPulse

Cloud-native video-viewing analytics & personalization platform.
Big Data Technologies & Cloud Computing capstone · 3 members · 3-week build.

Synthetic viewing telemetry → local/S3 Bronze Parquet → PySpark Silver/Gold and Spark MLlib ALS
→ DuckDB over Gold Parquet → User and Executive Streamlit portals.

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

1. Install Python 3.11 and Java 17+, then run `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e .`.
2. Local mode needs no cloud credentials. Generate sample events: `streampulse generate --events 10000 --output data/raw`.
3. Ingest all generated batches: `for file in data/raw/events-*.parquet; do streampulse ingest --source "$file"; done`.
4. Run Spark ETL and ALS: `streampulse process --bronze data/bronze/events --gold data/gold`.
5. Launch Streamlit: `streamlit run app/streamlit_app.py`. Run tests with `pytest -q`.

## Status

Implemented: generator, Parquet, local/S3 ingestion code, PySpark Silver/Gold and ALS, DuckDB serving, and both portal views. Verified here: generation, local Bronze, DuckDB, configuration, and ranking-metric tests. Spark requires Java and was not executed in the authoring environment; AWS and Databricks were not configured or cloud-tested. See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).
