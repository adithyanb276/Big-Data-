"""DuckDB queries over exported Gold Parquet datasets."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class GoldStore:
    """Small query facade that reads Gold Parquet without loading every table."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.connection = duckdb.connect(database=":memory:")

    def table_exists(self, name: str) -> bool:
        return bool(list((self.root / name).glob("*.parquet"))) if (self.root / name).is_dir() else False

    def query(self, name: str, *, limit: int = 10_000) -> pd.DataFrame:
        """Read a table by known name, returning an empty frame when absent."""
        if not name.replace("_", "").isalnum():
            raise ValueError("Invalid Gold table name")
        path = self.root / name
        if not self.table_exists(name):
            return pd.DataFrame()
        return self.connection.execute(
            "SELECT * FROM read_parquet(?) LIMIT ?", [str(path / "**/*.parquet"), limit]
        ).fetchdf()

    def user_recommendations(self, user_id: int, *, limit: int = 20) -> pd.DataFrame:
        """Return one user's precomputed recommendations without loading the full table."""
        path = self.root / "recommendations"
        if not self.table_exists("recommendations"):
            return pd.DataFrame()
        return self.connection.execute(
            "SELECT * FROM read_parquet(?) WHERE user_id = ? ORDER BY rank LIMIT ?",
            [str(path / "**/*.parquet"), user_id, limit],
        ).fetchdf()

    def available_users(self, *, limit: int = 1000) -> pd.DataFrame:
        """Return distinct user IDs from activity, with recommendation-only fallback."""
        for table in ("churn_risk", "silver_events", "recommendations"):
            path = self.root / table
            if self.table_exists(table):
                return self.connection.execute(
                    'SELECT DISTINCT user_id FROM read_parquet(?) ORDER BY user_id LIMIT ?',
                    [str(path / "**/*.parquet"), limit],
                ).fetchdf()
        return pd.DataFrame(columns=["user_id"])

    def filtered(
        self, name: str, *, device: str | None = None,
        start_date: str | None = None, end_date: str | None = None,
        limit: int = 10_000,
    ) -> pd.DataFrame:
        """Apply supported filters using bound parameters against Parquet."""
        if not name.replace("_", "").isalnum():
            raise ValueError("Invalid Gold table name")
        path = self.root / name
        if not self.table_exists(name):
            return pd.DataFrame()
        predicates, values = [], [str(path / "**/*.parquet")]
        if device and device != "All" and name in {"qos_5min", "device_distribution"}:
            predicates.append("device = ?")
            values.append(device)
        date_column = "window_start" if name == "qos_5min" else "date"
        if start_date and name in {"qos_5min", "device_distribution", "dau"}:
            predicates.append(f'CAST("{date_column}" AS DATE) >= ?')
            values.append(start_date)
        if end_date and name in {"qos_5min", "device_distribution", "dau"}:
            predicates.append(f'CAST("{date_column}" AS DATE) <= ?')
            values.append(end_date)
        where = " WHERE " + " AND ".join(predicates) if predicates else ""
        values.append(limit)
        return self.connection.execute(
            f"SELECT * FROM read_parquet(?) {where} LIMIT ?", values
        ).fetchdf()

    def freshness(self) -> str:
        files = [file for file in self.root.rglob("*.parquet") if file.is_file()]
        if not files:
            return "No Gold Parquet data found"
        newest = max(file.stat().st_mtime for file in files)
        return pd.Timestamp(newest, unit="s", tz="UTC").strftime("%Y-%m-%d %H:%M UTC")

    def close(self) -> None:
        self.connection.close()


def explanation_for_user(history: pd.DataFrame, movie_genre: str) -> str:
    """Generate a factual content explanation from observed genre history."""
    if history.empty or "genre" not in history:
        return "Recommended from viewing activity; genre history is unavailable."
    matching = int((history["genre"] == movie_genre).sum())
    if matching:
        return f"You watched {matching} title(s) in {movie_genre}."
    return f"A {movie_genre} pick beyond your most-watched genres."