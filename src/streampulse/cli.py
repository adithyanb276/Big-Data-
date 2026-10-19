"""Command line entry points for local generation, ingestion, and processing."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

from streampulse.config import Settings
from streampulse.generator import generate_parquet, movie_catalogue
from streampulse.ingestion import ingest_file
from streampulse.processing import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="streampulse")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--events", type=int, default=10_000)
    generate.add_argument("--users", type=int, default=10_000)
    generate.add_argument("--movies", type=int, default=1_000)
    generate.add_argument("--batch-size", type=int, default=5_000)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--output", type=Path, default=Path("data/raw"))
    generate.add_argument("--malformed-rate", type=float, default=0)
    generate.add_argument("--missing-rate", type=float, default=0)
    process = commands.add_parser("process")
    process.add_argument("--bronze", type=Path, default=Path("data/bronze/events"))
    process.add_argument("--gold", type=Path, default=Path("data/gold"))
    process.add_argument("--top-n", type=int, default=10)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--source", type=Path, required=True)
    ingest.add_argument("--dry-run", action="store_true")
    ingest.add_argument("--local-root", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.command == "generate":
        summary = generate_parquet(
            args.output, event_count=args.events, users=args.users, movies=args.movies,
            batch_size=args.batch_size, seed=args.seed,
            malformed_rate=args.malformed_rate, missing_rate=args.missing_rate,
        )
        pq.write_table(pa.Table.from_pylist(movie_catalogue(args.movies)), args.output / "movie_catalogue.parquet")
        print(summary)
    elif args.command == "ingest":
        settings = Settings.from_env()
        client = boto3.client("s3", region_name=settings.aws_region) if settings.mode == "cloud" and not args.dry_run else None
        print(ingest_file(
            args.source, mode=settings.mode,
            local_root=args.local_root or settings.data_dir / "bronze/events",
            s3_bucket=settings.s3_bucket, s3_prefix=settings.s3_prefix,
            s3_client=client, dry_run=args.dry_run,
        ))
    elif args.command == "process":
        print(run_pipeline(args.bronze, args.gold, als_top_n=args.top_n))


if __name__ == "__main__":
    main()