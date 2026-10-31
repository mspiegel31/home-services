#!/bin/sh
# Entrypoint of the Strata lanes.
#
# Upstream's 0.2.x docker/entrypoint.sh drives `strata launch --no-tui` from
# MODEL/FAMILY/CONTEXT-style env and auto-moves /data/{models,packs,mtp} into
# /data/Strata-data — a layout the model-more PVC does not use: its
# /data/packs, /data/models and /data/mtp are referenced in place by the lane
# run configs, and the setup-written configs live in /data/config. This
# entrypoint skips the launch path entirely and drives the supported
# `strata serve --config <run-config.json>`, which at 0.2.7 honors the
# hand-authored "exe"/"args" form: an absolute cfg["exe"] is exec'd as-is
# (serve/server.py resolves only relative ones against cfg["cwd"]), and the
# engine argv comes from cfg["args"] plus the server's own derived flags.
# Nothing is downloaded, packed or tuned here; a lane serves an
# already-prepared model (bootstrap/strata-*-prepare-job.yaml).
set -e

APP=/opt/strata
STRATA="$APP/terminal/bin/strata"
PY="$APP/terminal/python/bin/python3"
EXPORTER=/opt/strata-exporter
STRATA_DATA="${STRATA_DATA:-/data}"

say() { printf '%s\n' "$*"; }
die() { printf '[X] %s\n' "$*" >&2; exit "${2:-1}"; }

# The engine ships AVX2-baseline (BUILD.json portable=true): a host without
# AVX2 dies with SIGILL in ggml_cpu_init, not a clean error. A warning, not a
# stop: the flags file can be wrong in a VM, and STRATA_CPUINFO is for tests.
cpuinfo="${STRATA_CPUINFO:-/proc/cpuinfo}"
if [ -r "$cpuinfo" ] && grep -q '^flags' "$cpuinfo" && ! grep -m1 '^flags' "$cpuinfo" | grep -qw avx2; then
  say "WARNING: this host CPU has no AVX2. The engine in this image is built for CPUs with AVX2, so it may stop"
  say "  with 'illegal instruction' (exit 132)."
fi

# Which run config this lane serves. CONFIG wins; otherwise the config the
# setup pass recorded for FAMILY/MODEL on the volume (qwen carries no prefix,
# the tag is the lowercased model name — /data/config/strata-<tag>.json).
FAMILY="${FAMILY:-qwen}"
MODEL="${MODEL:-}"
case "$FAMILY" in qwen) prefix="" ;; *) prefix="${FAMILY}-" ;; esac
tag="${prefix}$(printf '%s' "$MODEL" | tr 'A-Z' 'a-z')"
cfg="$STRATA_DATA/config/strata-$tag.json"
mkdir -p "$STRATA_DATA/config"

if [ -n "${CONFIG:-}" ]; then
  [ -f "$CONFIG" ] || die "CONFIG=$CONFIG does not exist." 1
  # A config already under $STRATA_DATA is served in place (it is the PVC
  # copy and carries the lane's real paths); anything else — a read-only
  # git-sync volume a config might come from — is copied onto the writable
  # volume first, because the engine's runtime writes next to the config it
  # is given (log files, shared settings).
  case "$CONFIG" in
    "$STRATA_DATA"/*) served="$CONFIG" ;;
    *) cp -f "$CONFIG" "$cfg"; served="$cfg" ;;
  esac
  say "Config: $served (from CONFIG)"
else
  [ -f "$cfg" ] || die "no run config for FAMILY=$FAMILY MODEL=$MODEL: $cfg does not exist. This image serves an already-prepared model; run the prepare job or set CONFIG to a run-config json." 1
  served="$cfg"
  say "Config: $served (from MODEL $MODEL)"
fi

# Fold the standard multi-session cache flags and the lane env (PARALLEL,
# STRATA_VRAM_RESERVE_MIB, STRATA_PLE_IO, STRATA_VISION_MMPROJ) into the
# config before serving. Idempotent; the env the lane declares wins.
"$PY" "$EXPORTER/merge_args.py" "$served"

if [ "${STRATA_ENTRYPOINT_CHECK:-0}" = "1" ]; then
  # Dry run for CI and first bring-up: the CLI's own plan validates the
  # rendered config and resolves the engine exe without touching the GPU.
  exec "$STRATA" serve --config "$served" --plan --output json
fi

# HOST/PORT stay env-driven (the config also carries them; the flags win).
exec "$STRATA" serve --config "$served" --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
