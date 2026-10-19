"""FastAPI endpoints serving precomputed StreamPulse Gold Parquet."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from streampulse.serving import GoldStore

load_dotenv()


class HealthResponse(BaseModel):
    status: str
    data_available: bool
    data_mode: str
    sample_data: bool
    available_tables: list[str]


class OverviewResponse(BaseModel):
    total_events: int = 0
    total_sessions: int = 0
    daily_active_users: int = 0
    completed_views: int = 0
    completion_rate: float = 0.0
    average_buffer_ms: float = 0.0
    data_available: bool = False
    sample_data: bool = False


class TableResponse(BaseModel):
    data: list[dict[str, Any]]
    count: int
    data_available: bool
    sample_data: bool


class RecommendationResponse(TableResponse):
    user_id: int
    status: str


def _data_root() -> Path:
    return Path(os.getenv("STREAMPULSE_GOLD_DIR", "data/gold"))


def _sample_flag() -> bool:
    configured = os.getenv("STREAMPULSE_SAMPLE_DATA")
    return bool(configured and configured.lower() in {"1", "true", "yes"})


def _clean_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    safe = frame.astype(object).where(pd.notna(frame), None)
    return safe.to_dict(orient="records")


def get_store() -> Iterator[GoldStore]:
    store = GoldStore(_data_root())
    try:
        yield store
    finally:
        store.close()


def _table_response(store: GoldStore, table: str, *, limit: int = 500) -> TableResponse:
    frame = store.query(table, limit=limit)
    return TableResponse(
        data=_clean_records(frame), count=len(frame), data_available=not frame.empty,
        sample_data=_sample_flag(),
    )


def _add_catalogue(frame: pd.DataFrame) -> pd.DataFrame:
    catalogue_path = Path(os.getenv("STREAMPULSE_CATALOGUE_PATH", "data/raw/movie_catalogue.parquet"))
    if frame.empty or not catalogue_path.exists():
        return frame
    catalogue = pd.read_parquet(catalogue_path)
    return frame.merge(catalogue, on="movie_id", how="left")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="StreamPulse API", version="0.2.0",
    description="Read-only API over precomputed StreamPulse Gold Parquet datasets.",
    lifespan=lifespan,
)

origins = [item.strip() for item in os.getenv(
    "STREAMPULSE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=False,
    allow_methods=["GET"], allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health(store: GoldStore = Depends(get_store)) -> HealthResponse:
    tables = [
        "analytics_summary", "qos_5min", "completion_by_title", "device_distribution",
        "dau", "churn_risk", "completion_funnel", "recommendations",
    ]
    available = [table for table in tables if store.table_exists(table)]
    return HealthResponse(
        status="ok" if available else "degraded", data_available=bool(available),
        data_mode=os.getenv("STREAMPULSE_MODE", "local").lower(),
        sample_data=_sample_flag(), available_tables=available,
    )


@app.get("/api/overview", response_model=OverviewResponse)
def overview(store: GoldStore = Depends(get_store)) -> OverviewResponse:
    summary_frame = store.query("analytics_summary", limit=1)
    summary = summary_frame.iloc[0].to_dict() if not summary_frame.empty else {}
    dau = store.query("dau")
    if not dau.empty and "date" in dau:
        dau = dau.sort_values("date")
    daily_active = int(dau.iloc[-1]["daily_active_users"]) if not dau.empty else 0
    funnel = store.query("completion_funnel")
    completed = int(funnel["completions"].fillna(0).sum()) if not funnel.empty and "completions" in funnel else 0
    return OverviewResponse(
        total_events=int(summary.get("total_events", 0) or 0),
        total_sessions=int(summary.get("total_sessions", 0) or 0),
        daily_active_users=daily_active,
        completed_views=completed,
        completion_rate=float(summary.get("completion_rate", 0) or 0),
        average_buffer_ms=float(summary.get("avg_buffer_ms", 0) or 0),
        data_available=not summary_frame.empty,
        sample_data=_sample_flag(),
    )


@app.get("/api/analytics/qos", response_model=TableResponse)
def qos(
    device: str | None = None, start_date: str | None = None, end_date: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000), store: GoldStore = Depends(get_store),
) -> TableResponse:
    frame = store.filtered("qos_5min", device=device, start_date=start_date, end_date=end_date, limit=limit)
    return TableResponse(data=_clean_records(frame), count=len(frame), data_available=not frame.empty, sample_data=_sample_flag())


@app.get("/api/analytics/content", response_model=TableResponse)
def content(
    limit: int = Query(default=500, ge=1, le=5000), store: GoldStore = Depends(get_store),
) -> TableResponse:
    frame = _add_catalogue(store.query("completion_by_title", limit=limit))
    return TableResponse(data=_clean_records(frame), count=len(frame), data_available=not frame.empty, sample_data=_sample_flag())


@app.get("/api/analytics/devices", response_model=TableResponse)
def devices(
    start_date: str | None = None, end_date: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000), store: GoldStore = Depends(get_store),
) -> TableResponse:
    frame = store.filtered("device_distribution", start_date=start_date, end_date=end_date, limit=limit)
    return TableResponse(data=_clean_records(frame), count=len(frame), data_available=not frame.empty, sample_data=_sample_flag())


@app.get("/api/analytics/users", response_model=TableResponse)
def users_activity(
    limit: int = Query(default=500, ge=1, le=5000), store: GoldStore = Depends(get_store),
) -> TableResponse:
    dau = store.query("dau", limit=limit)
    return TableResponse(data=_clean_records(dau), count=len(dau), data_available=not dau.empty, sample_data=_sample_flag())


@app.get("/api/users", response_model=TableResponse)
def users(
    limit: int = Query(default=1000, ge=1, le=5000), store: GoldStore = Depends(get_store),
) -> TableResponse:
    frame = store.available_users(limit=limit)
    return TableResponse(data=_clean_records(frame), count=len(frame), data_available=not frame.empty, sample_data=_sample_flag())


@app.get("/api/recommendations/{user_id}", response_model=RecommendationResponse)
def recommendations(
    user_id: int, limit: int = Query(default=10, ge=1, le=100),
    store: GoldStore = Depends(get_store),
) -> RecommendationResponse:
    frame = store.user_recommendations(user_id, limit=limit)
    status = "available"
    if frame.empty:
        popular = store.query("completion_by_title", limit=5000)
        if not popular.empty and "views" in popular:
            popular = popular.sort_values(["views", "movie_id"], ascending=[False, True]).head(limit).copy()
            popular["rank"] = range(1, len(popular) + 1)
            max_views = max(float(popular["views"].max()), 1.0)
            popular["score"] = popular["views"].astype(float) / max_views
            popular["recommendation_source"] = "popularity"
            frame = popular
            status = "popularity_fallback"
    if not frame.empty:
        catalogue_path = Path(os.getenv("STREAMPULSE_CATALOGUE_PATH", "data/raw/movie_catalogue.parquet"))
        if catalogue_path.exists():
            frame = _add_catalogue(frame)
        else:
            frame["title"] = frame["movie_id"].map(lambda movie: f"Title {movie}")
            frame["genre"] = None
        if "recommendation_source" not in frame:
            frame["recommendation_source"] = "als"
        return RecommendationResponse(
            user_id=user_id, status=status, data=_clean_records(frame), count=len(frame),
            data_available=True, sample_data=_sample_flag(),
        )
    return RecommendationResponse(
        user_id=user_id, status="unavailable", data=[], count=0, data_available=False,
        sample_data=_sample_flag(),
    )