#!/bin/sh
# Alloy's vllm_backends scrape reads :8000, where upstream's engine serves JSON.
set -e
/opt/strata/.venv/bin/python /opt/strata-exporter/metrics_exporter.py &
exec /opt/strata/docker-entrypoint.sh "$@"
