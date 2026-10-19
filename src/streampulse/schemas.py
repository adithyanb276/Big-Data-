"""Canonical event fields and lightweight record validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pyarrow as pa

EVENT_TYPES = {"play", "pause", "seek", "buffer", "complete"}
EVENT_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string()),
        pa.field("user_id", pa.int64()),
        pa.field("movie_id", pa.int64()),
        pa.field("session_id", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("position_ms", pa.int64()),
        pa.field("duration_ms", pa.int64()),
        pa.field("bitrate", pa.float64()),
        pa.field("buffer_ms", pa.int64()),
        pa.field("device", pa.string()),
        pa.field("app_version", pa.string()),
        pa.field("event_ts", pa.timestamp("us")),
    ]
)


def validate_event(event: dict[str, Any]) -> list[str]:
    """Return all contract violations for an event without mutating it."""
    errors: list[str] = []
    for field in EVENT_SCHEMA.names:
        if event.get(field) is None:
            errors.append(f"{field} is required")
    if errors:
        return errors
    if not isinstance(event["event_ts"], datetime):
        errors.append("event_ts must be a datetime")
    if event["event_type"] not in EVENT_TYPES:
        errors.append("event_type is not supported")
    for field in ("user_id", "movie_id", "position_ms", "duration_ms", "buffer_ms"):
        if not isinstance(event[field], int) or event[field] < 0:
            errors.append(f"{field} must be a non-negative integer")
    if event["duration_ms"] <= 0:
        errors.append("duration_ms must be positive")
    if event["position_ms"] > event["duration_ms"]:
        errors.append("position_ms cannot exceed duration_ms")
    return errors