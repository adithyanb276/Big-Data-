"""PySpark Silver/Gold transformations and implicit-feedback ALS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

EVENT_COLUMNS = [
    "event_id", "user_id", "movie_id", "session_id", "event_type", "position_ms",
    "duration_ms", "bitrate", "buffer_ms", "device", "app_version", "event_ts",
]


def clean_events(raw: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Cast contract types, report malformed rows, and deduplicate by event_id."""
    from pyspark.sql import functions as F

    missing = set(EVENT_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Input schema missing event fields: {sorted(missing)}")
    typed = raw.select(
        F.col("event_id").cast("string"), F.col("user_id").cast("long"),
        F.col("movie_id").cast("long"), F.col("session_id").cast("string"),
        F.col("event_type").cast("string"), F.col("position_ms").cast("long"),
        F.col("duration_ms").cast("long"), F.col("bitrate").cast("double"),
        F.col("buffer_ms").cast("long"), F.col("device").cast("string"),
        F.col("app_version").cast("string"), F.to_timestamp("event_ts").alias("event_ts"),
    )
    valid = (
        F.col("event_id").isNotNull() & F.col("user_id").isNotNull()
        & F.col("movie_id").isNotNull() & F.col("session_id").isNotNull()
        & F.col("event_type").isin("play", "pause", "seek", "buffer", "complete")
        & F.col("position_ms").isNotNull() & (F.col("position_ms") >= 0)
        & F.col("duration_ms").isNotNull() & (F.col("duration_ms") > 0)
        & (F.col("position_ms") <= F.col("duration_ms"))
        & F.col("bitrate").isNotNull() & (F.col("bitrate") >= 0)
        & F.col("buffer_ms").isNotNull() & (F.col("buffer_ms") >= 0)
        & F.col("device").isNotNull() & F.col("app_version").isNotNull()
        & F.col("event_ts").isNotNull()
    )
    valid_events = typed.filter(valid).dropDuplicates(["event_id"])
    invalid_events = typed.filter(~F.coalesce(valid, F.lit(False)))
    return valid_events, invalid_events


def build_gold(events: DataFrame, invalid_count: int = 0) -> dict[str, DataFrame]:
    """Build contract-aligned analytics tables from valid, deduplicated events."""
    from pyspark.sql import Window, functions as F

    sessions = events.groupBy("session_id", "user_id", "movie_id", "device").agg(
        F.max(F.col("position_ms") / F.col("duration_ms")).alias("completion_fraction"),
        F.max(F.when(F.col("event_type") == "complete", 1).otherwise(0)).alias("completed"),
        F.min("event_ts").alias("session_start"), F.max("event_ts").alias("session_end"),
    )
    qos = events.withColumn("window_start", F.window("event_ts", "5 minutes").start).groupBy(
        "window_start", "device"
    ).agg(
        (F.sum(F.when(F.col("event_type") == "complete", 1).otherwise(0)) /
         F.greatest(F.sum(F.when(F.col("event_type") == "play", 1).otherwise(0)), F.lit(1))).alias("completion_rate"),
        (F.sum("buffer_ms") / F.greatest(F.sum("duration_ms"), F.lit(1))).alias("rebuffer_ratio"),
        F.avg("bitrate").alias("avg_bitrate"),
        F.lit(float(invalid_count) / max(events.count() + invalid_count, 1)).alias("error_rate"),
    )
    title = sessions.groupBy("movie_id").agg(
        F.count("*").alias("views"), F.avg("completion_fraction").alias("avg_completion"),
        F.avg(1 - F.col("completion_fraction")).alias("drop_off_point"),
    )
    device = sessions.withColumn("date", F.to_date("session_start")).groupBy("date", "device").agg(
        F.count("*").alias("sessions"),
    ).withColumn(
        "distribution", F.col("sessions") / F.sum("sessions").over(Window.partitionBy("date")),
    )
    dau = events.withColumn("date", F.to_date("event_ts")).groupBy("date").agg(
        F.countDistinct("user_id").alias("daily_active_users"),
    )
    user = sessions.groupBy("user_id").agg(
        F.count("*").alias("session_count"), F.avg("completion_fraction").alias("avg_completion"),
        F.max("session_end").alias("last_seen"),
    ).withColumn(
        "risk_score",
        F.least(F.lit(1.0), F.greatest(F.lit(0.0),
            (F.lit(1.0) - F.col("avg_completion")) * 0.55
            + F.when(F.datediff(F.current_date(), F.to_date("last_seen")) > 14, 0.3).otherwise(0.0)
            + F.when(F.col("session_count") < 2, 0.15).otherwise(0.0))),
    ).withColumn(
        "risk_category", F.when(F.col("risk_score") >= 0.7, "high")
        .when(F.col("risk_score") >= 0.4, "medium").otherwise("low"),
    ).withColumn(
        "contributing_indicators", F.concat_ws(",",
            F.when(F.col("avg_completion") < 0.5, F.lit("low_completion")),
            F.when(F.col("session_count") < 2, F.lit("low_frequency")),
            F.when(F.datediff(F.current_date(), F.to_date("last_seen")) > 14, F.lit("inactive_14d"))),
    ).select("user_id", "risk_score", "risk_category", "contributing_indicators")
    funnel = events.groupBy("movie_id").agg(
        F.sum(F.when(F.col("event_type") == "play", 1).otherwise(0)).alias("plays"),
        F.sum(F.when(F.col("event_type") == "pause", 1).otherwise(0)).alias("pauses"),
        F.sum(F.when(F.col("event_type") == "complete", 1).otherwise(0)).alias("completions"),
    )
    summary = events.agg(
        F.count("*").alias("total_events"), F.countDistinct("session_id").alias("total_sessions"),
        F.countDistinct("user_id").alias("active_users"), F.avg("buffer_ms").alias("avg_buffer_ms"),
    ).crossJoin(sessions.agg(F.avg("completion_fraction").alias("completion_rate")))
    return {
        "qos_5min": qos, "completion_by_title": title,
        "device_distribution": device, "dau": dau, "churn_risk": user,
        "completion_funnel": funnel, "analytics_summary": summary,
    }


def ranking_metrics(
    actual: dict[int, set[int]], predicted: dict[int, list[int]], k: int,
) -> dict[str, float]:
    """Compute macro Precision@K and NDCG@K over users with held-out positives."""
    if k < 1:
        raise ValueError("k must be positive")
    precisions, ndcgs = [], []
    import math
    for user_id, relevant in actual.items():
        if not relevant:
            continue
        ranked = predicted.get(user_id, [])[:k]
        hits = [1 if item in relevant else 0 for item in ranked]
        precisions.append(sum(hits) / k)
        dcg = sum(hit / math.log2(position + 2) for position, hit in enumerate(hits))
        ideal = sum(1 / math.log2(position + 2) for position in range(min(len(relevant), k)))
        ndcgs.append(dcg / ideal if ideal else 0.0)
    return {
        "precision_at_k": sum(precisions) / len(precisions) if precisions else 0.0,
        "ndcg_at_k": sum(ndcgs) / len(ndcgs) if ndcgs else 0.0,
        "evaluated_users": len(precisions),
    }


def train_recommendations(
    events: DataFrame, *, top_n: int = 10, rank: int = 12, reg_param: float = 0.1,
    alpha: float = 1.0, max_iter: int = 8, seed: int = 42,
) -> tuple[DataFrame, dict[str, Any]]:
    """Train implicit ALS, evaluate held-out ranking, and fill users via popularity."""
    from pyspark.ml.recommendation import ALS
    from pyspark.sql import Window, functions as F

    interactions = events.groupBy("user_id", "movie_id").agg(
        F.sum(F.when(F.col("event_type") == "complete", 2.0)
              .otherwise(F.col("position_ms") / F.col("duration_ms"))).alias("rating")
    ).withColumn("rating", F.greatest(F.col("rating"), F.lit(0.001))).select(
        F.col("user_id").cast("int").alias("user_id"),
        F.col("movie_id").cast("int").alias("movie_id"), "rating",
    )
    train, test = interactions.randomSplit([0.8, 0.2], seed=seed)
    estimator = ALS(
        userCol="user_id", itemCol="movie_id", ratingCol="rating", rank=rank,
        regParam=reg_param, alpha=alpha, maxIter=max_iter, implicitPrefs=True,
        coldStartStrategy="drop", nonnegative=True,
    )
    model = estimator.fit(train)
    test_users = test.select("user_id").distinct()
    tested = model.recommendForUserSubset(test_users, top_n).select("user_id", "recommendations")
    actual_rows = test.groupBy("user_id").agg(F.collect_set("movie_id").alias("actual")).collect()
    predicted_rows = tested.collect()
    actual = {row.user_id: set(row.actual) for row in actual_rows}
    predicted = {row.user_id: [r.movie_id for r in row.recommendations] for row in predicted_rows}
    metrics = ranking_metrics(actual, predicted, top_n)
    all_users = interactions.select("user_id").distinct()
    candidates = model.recommendForAllUsers(top_n * 3).select("user_id", F.explode("recommendations").alias("rec"))
    watched = interactions.select("user_id", "movie_id")
    candidates = candidates.select(
        "user_id", F.col("rec.movie_id").alias("movie_id"), F.col("rec.rating").alias("score")
    ).join(watched, ["user_id", "movie_id"], "left_anti")
    ranking = Window.partitionBy("user_id").orderBy(F.desc("score"), F.asc("movie_id"))
    personalized = candidates.withColumn("rank", F.row_number().over(ranking)).filter(
        F.col("rank") <= top_n
    ).select("user_id", "rank", "movie_id", "score")
    popularity = interactions.groupBy("movie_id").agg(F.sum("rating").alias("score")).orderBy(
        F.desc("score"), F.asc("movie_id")
    ).limit(top_n * 3)
    cold_users = all_users.join(personalized.select("user_id").distinct(), "user_id", "left_anti")
    cold_candidates = cold_users.crossJoin(F.broadcast(popularity)).join(
        watched, ["user_id", "movie_id"], "left_anti"
    )
    cold = cold_candidates.withColumn(
        "rank", F.row_number().over(Window.partitionBy("user_id").orderBy(F.desc("score"), F.asc("movie_id")))
    ).filter(F.col("rank") <= top_n).select(
        "user_id", "rank", "movie_id", "score", F.lit("popularity").alias("recommendation_source")
    )
    personalized = personalized.withColumn("recommendation_source", F.lit("als"))
    result = personalized.unionByName(cold).select(
        F.col("user_id").cast("long"), F.col("rank").cast("int"),
        F.col("movie_id").cast("long"), F.col("score").cast("double"), "recommendation_source",
    )
    return result, {
        **metrics, "algorithm": "Spark MLlib ALS implicit feedback",
        "parameters": {"rank": rank, "reg_param": reg_param, "alpha": alpha, "max_iter": max_iter, "top_n": top_n},
    }


def run_pipeline(bronze_path: str | Path, gold_path: str | Path, *, als_top_n: int = 10) -> dict[str, Any]:
    """Read Bronze Parquet, build Silver/Gold, train ALS, and write output Parquet."""
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("StreamPulse").getOrCreate()
    raw = spark.read.parquet(str(bronze_path))
    events, invalid = clean_events(raw)
    invalid_count = invalid.count()
    events.write.mode("overwrite").parquet(str(Path(gold_path) / "silver_events"))
    outputs = build_gold(events, invalid_count)
    for name, frame in outputs.items():
        frame.write.mode("overwrite").parquet(str(Path(gold_path) / name))
    recommendations, evaluation = train_recommendations(events, top_n=als_top_n)
    recommendations.write.mode("overwrite").parquet(str(Path(gold_path) / "recommendations"))
    (Path(gold_path) / "model_evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
    return {"valid_events": events.count(), "invalid_events": invalid_count, "evaluation": evaluation}