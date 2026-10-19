from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from streampulse.config import Settings
from streampulse.processing import ranking_metrics
from streampulse.serving import GoldStore, explanation_for_user


def test_duckdb_reads_parquet_and_applies_bound_filters(tmp_path: Path) -> None:
    table = tmp_path / "dau"
    table.mkdir()
    pq.write_table(pa.table({"date": ["2026-01-01", "2026-01-02"], "daily_active_users": [2, 4]}), table / "part.parquet")
    store = GoldStore(tmp_path)
    assert len(store.query("dau")) == 2
    assert len(store.filtered("dau", start_date="2026-01-02")) == 1
    assert store.query("not_ready").empty
    with pytest.raises(ValueError):
        store.query("dau;drop_table")


def test_ranking_metrics_against_known_example() -> None:
    result = ranking_metrics({1: {10, 11}, 2: {12}}, {1: [10, 12], 2: [12]}, 2)
    assert result["precision_at_k"] == pytest.approx(0.5)
    assert result["ndcg_at_k"] == pytest.approx((1 / (1 + 1 / 1.5849625007) + 1) / 2)
    assert result["evaluated_users"] == 2


def test_configuration_defaults_and_cloud_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STREAMPULSE_MODE", raising=False)
    monkeypatch.delenv("STREAMPULSE_S3_BUCKET", raising=False)
    assert Settings.from_env().mode == "local"
    monkeypatch.setenv("STREAMPULSE_MODE", "cloud")
    with pytest.raises(ValueError, match="S3_BUCKET"):
        Settings.from_env()


def test_recommendation_explanation_uses_observed_genres() -> None:
    import pandas as pd

    history = pd.DataFrame({"genre": ["Drama", "Drama", "Comedy"]})
    assert explanation_for_user(history, "Drama") == "You watched 2 title(s) in Drama."
    assert "beyond" in explanation_for_user(history, "Sci-Fi")


def test_dashboard_both_portals_load_without_gold_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("STREAMPULSE_GOLD_DIR", str(tmp_path / "gold"))
    app = AppTest.from_file("app/streamlit_app.py", default_timeout=20).run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Executive").run()
    assert not app.exception


def test_spark_cleaning_and_gold_metrics(spark) -> None:
    from streampulse.processing import build_gold, clean_events

    rows = [
        ("a", 1, 2, "s1", "play", 0, 100, 1200.0, 0, "web", "1", "2026-01-01 00:01:00"),
        ("b", 1, 2, "s1", "complete", 100, 100, 1200.0, 0, "web", "1", "2026-01-01 00:02:00"),
        ("b", 1, 2, "s1", "complete", 100, 100, 1200.0, 0, "web", "1", "2026-01-01 00:02:00"),
        ("bad", 1, 2, "s1", "wat", 0, 0, 0.0, 0, "web", "1", "2026-01-01 00:02:00"),
    ]
    frame = spark.createDataFrame(rows, [
        "event_id", "user_id", "movie_id", "session_id", "event_type", "position_ms",
        "duration_ms", "bitrate", "buffer_ms", "device", "app_version", "event_ts",
    ])
    clean, invalid = clean_events(frame)
    assert clean.count() == 2
    assert invalid.count() == 1
    gold = build_gold(clean, invalid_count=1)
    assert gold["qos_5min"].count() == 1
    assert gold["completion_by_title"].first()["views"] == 1
    assert {"risk_score", "risk_category", "contributing_indicators"}.issubset(gold["churn_risk"].columns)


def test_spark_als_trains_and_exports_ranked_recommendations(spark) -> None:
    from streampulse.processing import train_recommendations

    rows = []
    for user in range(8):
        for movie in range(6):
            rows.append((f"{user}-{movie}", user, movie, f"s-{user}-{movie}", "complete", 100, 100, 1000.0, 0, "web", "1", "2026-01-01 00:00:00"))
    events = spark.createDataFrame(rows, [
        "event_id", "user_id", "movie_id", "session_id", "event_type", "position_ms",
        "duration_ms", "bitrate", "buffer_ms", "device", "app_version", "event_ts",
    ])
    recommendations, metrics = train_recommendations(events, top_n=2, rank=2, max_iter=2)
    assert {"user_id", "rank", "movie_id", "score"}.issubset(recommendations.columns)
    assert recommendations.count() > 0
    assert "precision_at_k" in metrics and "ndcg_at_k" in metrics