#!/usr/bin/env bash
set -euo pipefail

export STREAMPULSE_MODE=local
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

python -m streampulse.cli generate --events "${EVENTS:-10000}" --output data/raw
for batch in data/raw/events-*.parquet; do
  python -m streampulse.cli ingest --source "$batch"
done
python -m streampulse.cli process --bronze data/bronze/events --gold data/gold