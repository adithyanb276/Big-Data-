# StreamPulse

Cloud-native video-viewing analytics & personalization platform.
Big Data Technologies & Cloud Computing capstone · 3 members · 3-week build.

Synthetic viewing telemetry → S3 data lake → Medallion Lakehouse on Databricks (PySpark)
→ ALS recommender (Spark MLlib) → dual-portal Streamlit app.

## Team & ownership

| Member | Workstream | Folder |
|---|---|---|
| **Fidal** | Cloud data engineering & ingestion | `ingestion/` |
| **Lubaba** | Big data processing & ML | `processing/` |
| **Adithyan** | Analytics engineering & serving | `app/` |

## Repo layout

```
streampulse/
├── README.md             ← you are here
├── ARCHITECTURE.md       ← the full design + diagram reference
├── CONTRIBUTING.md       ← how we work together (READ FIRST)
├── requirements.txt      ← pinned dependencies
├── .gitignore
├── docs/
│   ├── CONTRACTS.md       ← frozen data contracts (the APIs between us)
│   └── WORKPLAN.md        ← per-member checklists + 3-week schedule
├── ingestion/            ← Fidal: simulator, Boto3 uploader, Bronze
├── processing/           ← Lubaba: Silver ETL, ALS model, Gold
├── app/                  ← Adithyan: DuckDB serving, Streamlit portals
└── data/samples/         ← small mock datasets so everyone can start Day 1
```

## Quick start

1. Read `CONTRIBUTING.md`, then `ARCHITECTURE.md`, then `docs/WORKPLAN.md`.
2. `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your own AWS / Databricks creds (never commit `.env`).
4. Work on your branch, build against `data/samples/` first, open a PR when ready.

## Status

Week 1 — repo setup, data contracts being frozen. See `docs/WORKPLAN.md` for live task state.
