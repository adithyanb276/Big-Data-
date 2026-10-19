"""Idempotent local and S3 Bronze batch delivery."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pyarrow as pa
from botocore.exceptions import ClientError

LOGGER = logging.getLogger(__name__)


def batch_id(path: str | Path) -> str:
    """Use content identity so retries do not create duplicate objects."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest_file(
    source: str | Path, *, mode: str, local_root: str | Path = "data/bronze/events",
    s3_bucket: str | None = None, s3_prefix: str = "bronze/events", s3_client: Any = None,
    dry_run: bool = False, retries: int = 3,
) -> dict[str, Any]:
    """Deliver a validated Parquet file locally or to S3 using a stable key."""
    source_path = Path(source)
    metadata = pq.read_metadata(source_path)
    expected = {
        "event_id", "user_id", "movie_id", "session_id", "event_type", "position_ms",
        "duration_ms", "bitrate", "buffer_ms", "device", "app_version", "event_ts",
    }
    if not expected.issubset(set(metadata.schema.names)):
        raise ValueError(f"Parquet schema missing fields: {sorted(expected - set(metadata.schema.names))}")
    identifier = batch_id(source_path)
    batch = {"batch_id": identifier, "records": metadata.num_rows, "source": source_path.name}
    if dry_run:
        return {**batch, "dry_run": True}
    source_table = pq.read_table(source_path)
    partitions: dict[tuple[str, str], list[int]] = {}
    for row_index, event_ts in enumerate(source_table.column("event_ts").to_pylist()):
        partitions.setdefault((event_ts.strftime("%Y-%m-%d"), event_ts.strftime("%H")), []).append(row_index)
    delivered = []
    preexisting = []
    if mode == "local":
        target_root = Path(local_root)
        for (day, hour), indices in partitions.items():
            partition_table = source_table.take(pa.array(indices))
            partition_id = hashlib.sha256(f"{identifier}:{day}:{hour}".encode()).hexdigest()
            target = target_root / f"dt={day}" / f"hr={hour}" / f"{partition_id}.parquet"
            target.parent.mkdir(parents=True, exist_ok=True)
            existed = target.exists()
            if not target.exists():
                pq.write_table(partition_table, target, compression="snappy")
            manifest = target.with_suffix(".json")
            partition_manifest = {**batch, "batch_id": partition_id, "records": len(indices), "date": day, "hour": hour}
            if not manifest.exists():
                manifest.write_text(json.dumps(partition_manifest, indent=2) + "\n")
            delivered.append({"path": str(target), "records": len(indices), "batch_id": partition_id})
            preexisting.append(existed)
        LOGGER.info("local batch delivered", extra=batch)
        return {**batch, "partitions": delivered, "already_present": all(preexisting)}
    if mode != "cloud" or not s3_bucket or s3_client is None:
        raise ValueError("cloud mode requires s3_bucket and a configured boto3 client")
    for (day, hour), indices in partitions.items():
        partition_table = source_table.take(pa.array(indices))
        buffer = io.BytesIO()
        pq.write_table(partition_table, buffer, compression="snappy")
        partition_id = hashlib.sha256(f"{identifier}:{day}:{hour}".encode()).hexdigest()
        key = f"{s3_prefix.strip('/')}/dt={day}/hr={hour}/{partition_id}.parquet"
        partition_manifest = {**batch, "batch_id": partition_id, "records": len(indices), "date": day, "hour": hour}
        for attempt in range(retries + 1):
            try:
                try:
                    s3_client.head_object(Bucket=s3_bucket, Key=key)
                    s3_client.put_object(
                        Bucket=s3_bucket, Key=key + ".json",
                        Body=json.dumps(partition_manifest).encode("utf-8"), ContentType="application/json",
                    )
                    delivered.append({"s3_key": key, "records": len(indices), "batch_id": partition_id, "already_present": True})
                    break
                except Exception as error:
                    status = getattr(error, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
                    if status != 404:
                        raise
                s3_client.put_object(Bucket=s3_bucket, Key=key, Body=buffer.getvalue())
                s3_client.put_object(
                    Bucket=s3_bucket, Key=key + ".json",
                    Body=json.dumps(partition_manifest).encode("utf-8"), ContentType="application/json",
                )
                delivered.append({"s3_key": key, "records": len(indices), "batch_id": partition_id, "already_present": False})
                break
            except Exception as error:
                if attempt >= retries:
                    raise
                if isinstance(error, ClientError):
                    status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
                    if status < 500 and status != 429:
                        raise
                time.sleep(min(2 ** attempt, 16))
    return {**batch, "partitions": delivered, "already_present": all(item["already_present"] for item in delivered)}