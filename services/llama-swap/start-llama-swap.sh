#!/usr/bin/env bash
set -euo pipefail

set -a
source /mnt/models/llama-swap/.env
set +a

exec llama-swap \
  --config /mnt/models/llama-swap/config.yml \
  --listen 0.0.0.0:11437