from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pyarrow.parquet as pq
from botocore.exceptions import ClientError

from streampulse.generator import generate_parquet, iter_events
from streampulse.ingestion import ingest_file
from streampulse.schemas import validate_event


def test_generator_is_reproducible_and_session_coherent(tmp_path: Path) -> None:
    first = list(iter_events(event_count=30, users=5, movies=8, seed=12))
    second = list(iter_events(event_count=30, users=5, movies=8, seed=12))
    assert first == second
    sessions: dict[str, set[tuple[int, int]]] = {}
    for event in first:
        sessions.setdefault(event["session_id"], set()).add((event["user_id"], event["movie_id"]))
        assert validate_event(event) == []
    assert all(len(values) == 1 for values in sessions.values())


def test_generator_writes_snappy_parquet_and_quality_counts(tmp_path: Path) -> None:
    summary = generate_parquet(
        tmp_path / "raw", event_count=37, batch_size=10, seed=7, malformed_rate=0.2,
    )
    files = sorted((tmp_path / "raw").glob("events-*.parquet"))
    assert summary["event_count"] == 37
    assert summary["invalid_count"] > 0
    assert sum(pq.read_metadata(path).num_rows for path in files) == 37
    assert pq.read_metadata(files[0]).row_group(0).column(0).compression == "SNAPPY"


def test_generator_preserves_configured_missing_values_in_bronze(tmp_path: Path) -> None:
    generate_parquet(tmp_path / "raw", event_count=20, batch_size=20, seed=71, missing_rate=1)
    source = next((tmp_path / "raw").glob("events-*.parquet"))
    table = pq.read_table(source)
    assert sum(table.column(field).null_count for field in ("device", "bitrate", "position_ms")) > 0


def test_local_ingestion_partitions_and_is_idempotent(tmp_path: Path) -> None:
    generate_parquet(tmp_path / "raw", event_count=120, batch_size=120, seed=1)
    source = next((tmp_path / "raw").glob("events-*.parquet"))
    first = ingest_file(source, mode="local", local_root=tmp_path / "bronze")
    again = ingest_file(source, mode="local", local_root=tmp_path / "bronze")
    assert sum(part["records"] for part in first["partitions"]) == 120
    assert first["partitions"]
    assert all("dt=" in part["path"] and "hr=" in part["path"] for part in first["partitions"])
    assert again["already_present"] is True


def test_ingestion_dry_run_does_not_create_bronze(tmp_path: Path) -> None:
    generate_parquet(tmp_path / "raw", event_count=2)
    source = next((tmp_path / "raw").glob("events-*.parquet"))
    result = ingest_file(source, mode="local", local_root=tmp_path / "bronze", dry_run=True)
    assert result["dry_run"] is True
    assert not (tmp_path / "bronze").exists()


def test_s3_ingestion_uploads_partition_and_skips_duplicate(tmp_path: Path) -> None:
    generate_parquet(tmp_path / "raw", event_count=4)
    source = next((tmp_path / "raw").glob("events-*.parquet"))
    client = Mock()
    client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadObject"
    )
    first = ingest_file(source, mode="cloud", s3_bucket="private-bucket", s3_client=client)
    assert first["partitions"][0]["already_present"] is False
    assert client.put_object.call_count == 2
    client.head_object.side_effect = None
    again = ingest_file(source, mode="cloud", s3_bucket="private-bucket", s3_client=client)
    assert again["already_present"] is True


def test_ingestion_rejects_parquet_without_event_contract(tmp_path: Path) -> None:
    import pyarrow as pa

    source = tmp_path / "wrong.parquet"
    pq.write_table(pa.table({"wrong": [1]}), source)
    import pytest

    with pytest.raises(ValueError, match="schema missing"):
        ingest_file(source, mode="local", local_root=tmp_path / "bronze")