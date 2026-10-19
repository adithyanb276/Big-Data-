from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi.testclient import TestClient

from app.main import app


def _write_table(root: Path, name: str, data: dict[str, list]) -> None:
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(data), target / "part-00000.parquet")


def test_health_and_overview_report_missing_gold_honestly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMPULSE_GOLD_DIR", str(tmp_path / "missing"))
    monkeypatch.delenv("STREAMPULSE_SAMPLE_DATA", raising=False)
    with TestClient(app) as client:
        health = client.get("/api/health")
        overview = client.get("/api/overview")
        assert health.status_code == 200
        assert health.json() == {
            "status": "degraded", "data_available": False, "data_mode": "local",
            "sample_data": False, "available_tables": [],
        }
        assert overview.json()["total_events"] == 0
        assert overview.json()["completed_views"] == 0
        assert overview.json()["data_available"] is False


def test_analytics_endpoints_serve_gold_parquet_and_filters(tmp_path: Path, monkeypatch) -> None:
    gold = tmp_path / "gold"
    _write_table(gold, "analytics_summary", {
        "total_events": [24], "total_sessions": [6], "active_users": [4],
        "completion_rate": [0.75], "avg_buffer_ms": [325.0],
    })
    _write_table(gold, "completion_funnel", {"movie_id": [3, 4], "plays": [10, 8], "pauses": [3, 2], "completions": [7, 4]})
    _write_table(gold, "dau", {"date": ["2026-01-01", "2026-01-02"], "daily_active_users": [2, 4]})
    _write_table(gold, "qos_5min", {
        "window_start": ["2026-01-01 00:00:00", "2026-01-01 00:05:00"],
        "device": ["web", "tv"], "completion_rate": [0.7, 0.5],
        "rebuffer_ratio": [0.01, 0.04], "avg_bitrate": [2500.0, 1500.0], "error_rate": [0.0, 0.0],
    })
    _write_table(gold, "device_distribution", {
        "date": ["2026-01-01", "2026-01-01"], "device": ["web", "tv"],
        "sessions": [8, 2], "distribution": [0.8, 0.2],
    })
    _write_table(gold, "completion_by_title", {
        "movie_id": [3], "views": [10], "avg_completion": [0.72], "drop_off_point": [0.28],
    })
    monkeypatch.setenv("STREAMPULSE_GOLD_DIR", str(gold))
    monkeypatch.setenv("STREAMPULSE_SAMPLE_DATA", "true")
    with TestClient(app) as client:
        overview = client.get("/api/overview").json()
        assert overview["total_events"] == 24
        assert overview["daily_active_users"] == 4
        assert overview["completed_views"] == 11
        assert overview["average_buffer_ms"] == 325
        assert overview["sample_data"] is True
        qos = client.get("/api/analytics/qos", params={"device": "web"}).json()
        assert qos["count"] == 1 and qos["data"][0]["device"] == "web"
        assert client.get("/api/analytics/content").json()["data"][0]["movie_id"] == 3
        assert client.get("/api/analytics/devices").json()["count"] == 2
        assert client.get("/api/analytics/users").json()["count"] == 2
        assert client.get("/api/health").json()["data_available"] is True


def test_recommendation_and_users_endpoints_join_catalogue(tmp_path: Path, monkeypatch) -> None:
    gold = tmp_path / "gold"
    _write_table(gold, "recommendations", {
        "user_id": [7], "rank": [1], "movie_id": [12], "score": [0.84],
        "recommendation_source": ["als"],
    })
    _write_table(gold, "churn_risk", {
        "user_id": [7], "risk_score": [0.2], "risk_category": ["low"], "contributing_indicators": [""]
    })
    _write_table(gold, "completion_by_title", {
        "movie_id": [12, 13], "views": [15, 9],
        "avg_completion": [0.72, 0.61], "drop_off_point": [0.28, 0.39],
    })
    catalogue = tmp_path / "movie_catalogue.parquet"
    pq.write_table(pa.table({"movie_id": [12], "title": ["Copper Harbor"], "genre": ["Drama"]}), catalogue)
    monkeypatch.setenv("STREAMPULSE_GOLD_DIR", str(gold))
    monkeypatch.setenv("STREAMPULSE_CATALOGUE_PATH", str(catalogue))
    with TestClient(app) as client:
        users = client.get("/api/users").json()
        assert users["data"] == [{"user_id": 7}]
        recommendation = client.get("/api/recommendations/7").json()
        assert recommendation["status"] == "available"
        assert recommendation["data"][0]["title"] == "Copper Harbor"
        assert recommendation["data"][0]["recommendation_source"] == "als"
        missing = client.get("/api/recommendations/999").json()
        assert missing["status"] == "popularity_fallback"
        assert missing["data"][0]["recommendation_source"] == "popularity"


def test_recommendations_are_unavailable_without_model_or_content(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMPULSE_GOLD_DIR", str(tmp_path / "empty"))
    with TestClient(app) as client:
        missing = client.get("/api/recommendations/999").json()
        assert missing["status"] == "unavailable" and missing["data"] == []


def test_cors_allows_local_vite_origin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMPULSE_GOLD_DIR", str(tmp_path / "empty"))
    with TestClient(app) as client:
        response = client.options("/api/health", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
        })
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"