# Contributing — How We Work Together

A 3-week project only works if nobody blocks anybody. These rules keep us moving in parallel.

## Golden rules

1. **Freeze the data contracts in Week 1.** `docs/CONTRACTS.md` is treated like an API. If a contract must change, announce it, bump the version, and tell the person downstream.
2. **Build against mocks first.** Use `data/samples/` so you never wait for someone else's real output. Lubaba doesn't wait for Fidal's live data; Adithyan doesn't wait for Lubaba's real model.
3. **Never commit secrets.** No AWS keys, no `.env`, no tokens. They go in `.env` (git-ignored) and in Streamlit secrets. If a secret is ever committed, rotate it immediately.

## Git workflow

- **`main` is protected** — no direct pushes. Everything lands via Pull Request.
- **One feature branch per piece of work**, named by owner/module:
  - `feat/ingestion-*` (Fidal), `feat/silver-*` / `feat/als-*` (Lubaba), `feat/ui-*` (Adithyan)
- **Open a PR** when a slice is done. At least **one teammate reviews** before merge.
- **Small, frequent commits** with clear messages. Suggested style:
  - `feat: add Boto3 batch uploader`, `fix: handle null bitrate in Silver`, `docs: update contract B`
- Pull `main` into your branch often to avoid painful merges.

## Code & environment conventions

- Python 3.11 is recommended. Install Java 17+ for local Spark, then `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e .`.
- Local mode needs no cloud configuration. Copy `.env.example` only to override defaults; never commit `.env`.
- Each person works inside their own top-level folder (`ingestion/`, `processing/`, `app/`). Shared helpers go in a small `common/` module if needed — agree before adding.
- Keep notebooks (Databricks) exported to the repo as `.py` or `.ipynb` so they're reviewable.
- One `requirements.txt` for the repo; note Databricks-only libs separately.

Generate a small dataset, run local ingestion, and `pytest -q` before opening a PR. See `docs/SETUP.md` for exact commands.

## Definition of Done (every task)

- Runs end-to-end on the sample data without errors.
- Output matches the relevant contract in `docs/CONTRACTS.md`.
- Committed on a branch, PR opened, reviewed, merged to `main`.
- A one-line note added to the task checklist in `docs/WORKPLAN.md`.

## Communication

- **Daily async standup** in the group chat: *what I did / what I'm doing / any blockers.*
- Flag blockers the moment they appear — a blocked teammate is the biggest risk to a 3-week timeline.
- Keep a short **decision log** at the bottom of `ARCHITECTURE.md` when you make a design call.
