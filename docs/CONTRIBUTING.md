# Team Contribution Guide

The three owners can work against the frozen contracts in [CONTRACTS.md](CONTRACTS.md): Fidal owns generation/ingestion/Bronze, Lubaba owns Spark Silver/ALS/Gold, and Adithyan owns DuckDB/FastAPI/React presentation. Contract changes require a version update and coordination with downstream owners.

Use a feature branch, keep secrets and generated data out of Git, and test a small local batch before review. Required baseline: Java 17+, Python 3.11, `pip install -r requirements.txt`, `pip install -e .`, `pytest -q`. See the root [CONTRIBUTING.md](../CONTRIBUTING.md) for the existing PR and review conventions.