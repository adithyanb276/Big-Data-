"""StreamPulse User and Executive portals over exported Gold datasets."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from streampulse.generator import movie_catalogue
from streampulse.serving import GoldStore, explanation_for_user

st.set_page_config(page_title="StreamPulse", layout="wide")
st.title("StreamPulse")
mode = os.getenv("STREAMPULSE_MODE", "local").upper()
st.caption(f"{mode} MODE | Demo analytics" if mode == "LOCAL" else "CLOUD MODE | configured runtime")
gold_path = Path(os.getenv("STREAMPULSE_GOLD_DIR", "data/gold"))
store = GoldStore(gold_path)
st.caption(f"Gold data refreshed: {store.freshness()}")
portal = st.sidebar.radio("Portal", ["User", "Executive"])

if portal == "User":
    st.header("Your watchlist")
    recs = store.query("recommendations")
    if recs.empty:
        st.info("No recommendation slate is available yet. Run the local pipeline to generate ALS recommendations.")
    else:
        user_id = int(st.selectbox("Demo user", sorted(recs["user_id"].dropna().unique().tolist())))
        user_recs = recs[recs["user_id"] == user_id].sort_values("rank")
        history = store.query("silver_events")
        watched = set(history.loc[history["user_id"] == user_id, "movie_id"].astype(int)) if not history.empty else set()
        catalogue = pd.DataFrame(movie_catalogue(max(int(recs["movie_id"].max()) + 1, 10)))
        if not history.empty:
            history = history[history["user_id"] == user_id].merge(catalogue, on="movie_id", how="left")
        user_recs = user_recs[~user_recs["movie_id"].isin(watched)].merge(catalogue, on="movie_id", how="left")
        if not user_recs.empty:
            for _, row in user_recs.iterrows():
                st.subheader(f"{int(row['rank']):02d}  {row.get('title', 'Title ' + str(row['movie_id']))}")
                genre = row.get("genre", "Unknown")
                source = row.get("recommendation_source", "als")
                source_label = "Popularity fallback" if source == "popularity" else "ALS personalized"
                st.write(f"{genre} | {source_label} | score {float(row['score']):.3f}")
                st.caption(explanation_for_user(history, genre))
        else:
            st.info("All available recommendations are already in your history. Try a different demo user.")
        st.subheader("Continue watching")
        if history.empty:
            st.caption("No viewing history is available for this user.")
        else:
            progress = history.groupby("movie_id").agg(position_ms=("position_ms", "max"), duration_ms=("duration_ms", "max")).reset_index()
            progress["completion"] = (progress["position_ms"] / progress["duration_ms"]).clip(0, 1)
            progress = progress[progress["completion"] < 1]
            st.dataframe(progress.merge(catalogue, on="movie_id", how="left")[["title", "genre", "completion"]], hide_index=True)
        st.caption("Popularity fallback is used for users without ALS recommendations; scores rank interaction strength and are not probabilities.")
else:
    st.header("Executive overview")
    summary = store.query("analytics_summary")
    qos_all = store.query("qos_5min")
    if summary.empty:
        st.warning("Gold analytics are not available. Generate events and run the processing pipeline.")
    else:
        row = summary.iloc[0]
        card_values = [
            ("total_events", "Events", ".0f"), ("total_sessions", "Sessions", ".0f"),
            ("active_users", "Active users", ".0f"), ("completion_rate", "Completion", ".1%"),
        ]
        cards = st.columns(4)
        for card, (key, label, fmt) in zip(cards, card_values):
            card.metric(label, format(row.get(key, 0), fmt))
        qos_metrics = [
            ("rebuffer_ratio", "Rebuffer ratio", ".2%"),
            ("avg_bitrate", "Average bitrate (Kbps)", ",.0f"),
            ("error_rate", "Invalid event rate", ".2%"),
        ]
        cards = st.columns(3)
        for card, (key, label, fmt) in zip(cards, qos_metrics):
            value = qos_all[key].mean() if not qos_all.empty and key in qos_all else 0
            card.metric(label, format(value, fmt))
    devices = store.query("device_distribution")
    selection = st.selectbox("Device filter", ["All"] + (sorted(devices["device"].dropna().unique().tolist()) if not devices.empty else []))
    date_cols = st.columns(2)
    start_date = date_cols[0].date_input("From date", value=None)
    end_date = date_cols[1].date_input("To date", value=None)
    start_text = start_date.isoformat() if start_date else None
    end_text = end_date.isoformat() if end_date else None
    qos = store.filtered("qos_5min", device=selection, start_date=start_text, end_date=end_text)
    if not qos.empty:
        st.subheader("Five-minute quality of service")
        st.plotly_chart(px.line(qos, x="window_start", y="completion_rate", color="device", title="Completion rate"), use_container_width=True)
        st.plotly_chart(px.line(qos, x="window_start", y="rebuffer_ratio", color="device", title="Rebuffer ratio"), use_container_width=True)
        st.dataframe(qos, hide_index=True)
    title = store.query("completion_by_title")
    if not title.empty:
        st.subheader("Completion by title")
        title_ids = ["All"] + sorted(title["movie_id"].astype(str).unique().tolist())
        selected_title = st.selectbox("Title filter", title_ids)
        filtered_title = title if selected_title == "All" else title[title["movie_id"].astype(str) == selected_title]
        st.plotly_chart(px.bar(filtered_title.sort_values("views", ascending=False).head(25), x="movie_id", y="avg_completion", hover_data=["views", "drop_off_point"]), use_container_width=True)
        st.download_button("Download title report", filtered_title.to_csv(index=False), "completion_by_title.csv", "text/csv")
    if not devices.empty:
        st.subheader("Device distribution")
        filtered_devices = store.filtered("device_distribution", device=selection, start_date=start_text, end_date=end_text)
        st.plotly_chart(px.bar(filtered_devices, x="date", y="distribution", color="device", barmode="stack"), use_container_width=True)
    dau = store.filtered("dau", start_date=start_text, end_date=end_text)
    if not dau.empty:
        st.subheader("Daily active users")
        st.plotly_chart(px.line(dau, x="date", y="daily_active_users"), use_container_width=True)
        st.download_button("Download DAU report", dau.to_csv(index=False), "dau.csv", "text/csv")
    funnel = store.query("completion_funnel")
    if not funnel.empty:
        st.subheader("Completion funnel")
        st.dataframe(funnel, hide_index=True)
    churn = store.query("churn_risk")
    if not churn.empty:
        st.subheader("Heuristic churn-risk categories")
        st.caption("Risk score is a transparent engagement heuristic, not a cancellation probability.")
        st.plotly_chart(px.histogram(churn, x="risk_category", color="risk_category"), use_container_width=True)
        st.download_button("Download churn report", churn.to_csv(index=False), "churn_risk.csv", "text/csv")
    evaluation_path = gold_path / "model_evaluation.json"
    if evaluation_path.exists():
        import json

        evaluation = json.loads(evaluation_path.read_text())
        st.subheader("Recommendation evaluation")
        score_cols = st.columns(3)
        score_cols[0].metric("Precision@K", f"{evaluation.get('precision_at_k', 0):.3f}")
        score_cols[1].metric("NDCG@K", f"{evaluation.get('ndcg_at_k', 0):.3f}")
        score_cols[2].metric("Evaluated users", f"{evaluation.get('evaluated_users', 0):,}")

if st.sidebar.button("Refresh Gold data"):
    st.rerun()