"""Bounded-memory synthetic video telemetry generation."""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from streampulse.schemas import EVENT_SCHEMA, validate_event

DEVICES = ("web", "ios", "android", "tv")
VERSIONS = ("3.2.0", "3.2.1", "3.3.0")
TITLES = (
    ("The Last Signal", "Sci-Fi"), ("Copper Harbor", "Drama"),
    ("Wild Current", "Documentary"), ("Paper Moons", "Romance"),
    ("Night Shift", "Thriller"), ("Small Worlds", "Comedy"),
    ("Deep Blue", "Adventure"), ("The Long Weekend", "Comedy"),
    ("Glass House", "Mystery"), ("Northern Lights", "Drama"),
)


def iter_events(
    *, event_count: int, users: int = 10_000, movies: int = 1_000,
    seed: int = 42, malformed_rate: float = 0, missing_rate: float = 0,
) -> Iterator[dict[str, Any]]:
    """Yield deterministic events with Zipf-skewed titles and plausible sessions."""
    if event_count < 0 or users < 1 or movies < 1:
        raise ValueError("event_count must be non-negative; users and movies must be positive")
    if not 0 <= malformed_rate <= 1 or not 0 <= missing_rate <= 1:
        raise ValueError("malformed_rate and missing_rate must be between 0 and 1")
    rng = random.Random(seed)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    event_types = ("play", "pause", "seek", "buffer", "complete")
    for index in range(event_count):
        session_index = index // 5
        offset = index % 5
        duration = rng.randint(600_000, 7_200_000)
        user_id = rng.randrange(users)
        movie = min(movies - 1, int(rng.paretovariate(1.35)) - 1)
        if offset:
            previous = session_index
            user_id = previous_user
            movie = previous_movie
            duration = previous_duration
        else:
            previous_user, previous_movie, previous_duration = user_id, movie, duration
        event_type = event_types[offset] if offset < len(event_types) else rng.choice(event_types)
        position = duration if event_type == "complete" else min(duration, offset * duration // 5 + rng.randint(0, duration // 10))
        event = {
            "event_id": f"{seed:08d}-{index:012d}",
            "user_id": user_id,
            "movie_id": movie,
            "session_id": f"session-{session_index:010d}",
            "event_type": event_type,
            "position_ms": position,
            "duration_ms": duration,
            "bitrate": float(rng.choice((750, 1500, 2500, 4000, 8000))),
            "buffer_ms": rng.randint(0, 12_000) if event_type == "buffer" else 0,
            "device": rng.choice(DEVICES),
            "app_version": rng.choice(VERSIONS),
            "event_ts": base + timedelta(seconds=index * 17 + rng.randrange(17)),
        }
        if rng.random() < malformed_rate:
            event["duration_ms"] = -1
        if rng.random() < missing_rate:
            event[rng.choice(("device", "bitrate", "position_ms"))] = None
        yield event


def generate_parquet(
    destination: str | Path, *, event_count: int = 10_000, users: int = 10_000,
    movies: int = 1_000, batch_size: int = 5_000, seed: int = 42,
    malformed_rate: float = 0, missing_rate: float = 0,
) -> dict[str, Any]:
    """Write Snappy Parquet batches with bounded memory and a summary manifest."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    iterator = iter_events(
        event_count=event_count, users=users, movies=movies, seed=seed,
        malformed_rate=malformed_rate, missing_rate=missing_rate,
    )
    records = written = invalid = 0
    batch_index = 0
    while True:
        rows = []
        try:
            for _ in range(batch_size):
                event = next(iterator)
                records += 1
                invalid += bool(validate_event(event))
                rows.append(event)
        except StopIteration:
            pass
        if not rows:
            break
        table = pa.Table.from_pylist(rows, schema=EVENT_SCHEMA)
        pq.write_table(table, root / f"events-{seed:08d}-{batch_index:012d}.parquet", compression="snappy")
        written += len(rows)
        batch_index += 1
    summary = {
        "event_count": written, "invalid_count": invalid, "seed": seed,
        "users": users, "movies": movies, "batch_size": batch_size,
        "schema": EVENT_SCHEMA.names,
    }
    (root / "generation_manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def movie_catalogue(movie_count: int = 1_000) -> list[dict[str, Any]]:
    """Return deterministic human-readable catalogue metadata for demo titles."""
    return [
        {"movie_id": movie_id, "title": TITLES[movie_id % len(TITLES)][0] + f" {movie_id // len(TITLES) + 1}",
         "genre": TITLES[movie_id % len(TITLES)][1]}
        for movie_id in range(movie_count)
    ]