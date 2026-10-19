"""Environment-backed configuration for local and AWS operation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mode: str = "local"
    data_dir: Path = Path("data")
    aws_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_prefix: str = "bronze/events"

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Settings":
        load_dotenv(env_file or None)
        mode = os.getenv("STREAMPULSE_MODE", "local").lower()
        if mode not in {"local", "cloud"}:
            raise ValueError("STREAMPULSE_MODE must be 'local' or 'cloud'")
        bucket = os.getenv("STREAMPULSE_S3_BUCKET")
        if mode == "cloud" and not bucket:
            raise ValueError("STREAMPULSE_S3_BUCKET is required in cloud mode")
        return cls(
            mode=mode,
            data_dir=Path(os.getenv("STREAMPULSE_DATA_DIR", "data")),
            aws_region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            s3_bucket=bucket,
            s3_prefix=os.getenv("STREAMPULSE_S3_PREFIX", "bronze/events").strip("/"),
        )