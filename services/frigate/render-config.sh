#!/bin/sh
set -e

if ! command -v envsubst >/dev/null 2>&1; then
  apk add --no-cache gettext > /dev/null 2>&1
fi

TEMPLATE="/git/current/services/frigate/config/config.yml"
OUTPUT="/config/config.yml"

while true; do
  if [ -f "$TEMPLATE" ]; then
    envsubst < "$TEMPLATE" > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT"
  fi
  sleep 10
done
