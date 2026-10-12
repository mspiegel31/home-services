#!/bin/sh
# Container entry for the Maya lane. Two paths:
#
#   * First boot (no config on /data): `maya.py --setup --yes` against the staged files. --yes
#     makes every answer the CLI's (--model/--context/--gpu/--draft) and answers the download
#     offer with its default n — a lane whose GGUFs are not staged stops with the exact curl
#     commands in its log instead of pulling 116 GB behind a request's first token. --no-start,
#     then the config maya.py wrote into /opt/maya (an image layer, gone on restart) is copied to
#     /data/config with its engine log moved beside it, so --report survives container rebuilds.
#   * Steady state: exec serve/server.py directly, NOT `maya.py --config`: maya.py waits on the
#     server with subprocess.call and dies on SIGTERM without forwarding it, killing the engine
#     mid-slot-save. server.py installs its own SIGTERM handler (engine QUIT + in-flight wrap-up,
#     serve/server.py "SIGTERM (llama-swap's cmdStop...)") — as PID 1 it is what docker stop
#     reaches. Grace: STRATA_ENGINE_QUIT_S 50 + STRATA_ENGINE_WRAP_S 40 < cmdStop --time 90 <
#     llama-swap unloadTimeout 120.
#
# Env: MODEL (a maya.py MODELS key: Maya-M, Maya-S-v2-IQ2_XXS, Maya-S24, Maya-L, ...), CONTEXT,
# GPU, HOST, PORT, PARALLEL, NO_VISION (1 = text only), API_KEY. CONTEXT and PARALLEL are
# re-applied to an installed config on every start (env wins, the way images/strata's
# merge_args.py treats its env), so retuning them is a Portainer env change + restart; every
# other setting is fixed at first boot — delete /data/config/maya-<model>.json to re-run setup.
# Engine knobs (STRATA_GLM_KV_INT8, STRATA_GLM_SEQ_CTX, STRATA_GLM_SLOT_KEEP, ...) need no
# wiring: server.py's child_env hands the container's os.environ to the engine.
set -e
cd /opt/maya || exit 1

DATA="${DATA:-/data}"
MODEL="${MODEL:-Maya-M}"
CONTEXT="${CONTEXT:-32768}"
GPU="${GPU:-0}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
PARALLEL="${PARALLEL:-}"
NO_VISION="${NO_VISION:-}"
API_KEY="${API_KEY:-}"

# write_config names the installed config after the lowercased MODELS key
quant=$(printf '%s' "$MODEL" | tr 'A-Z' 'a-z')
cfg="$DATA/config/maya-$quant.json"
mkdir -p "$DATA/config" "$DATA/models"

if [ ! -f "$cfg" ]; then
  set -- --setup --yes --model "$MODEL" --context "$CONTEXT" --models-dir "$DATA/models" \
         --gpu "$GPU" --host "$HOST" --port "$PORT" --draft mtp --no-start
  if [ -n "$PARALLEL" ]; then set -- "$@" --parallel "$PARALLEL"; fi
  if [ -n "$NO_VISION" ] && [ "$NO_VISION" != "0" ]; then set -- "$@" --no-vision; fi
  .venv/bin/python maya.py "$@"
  if [ ! -f "/opt/maya/maya-$quant.json" ]; then
    echo "setup wrote no maya-$quant.json: the model files must be staged under" \
         "$DATA/models/$MODEL/ (the download commands are in the messages above)" >&2
    exit 1
  fi
  .venv/bin/python - "$quant" "$DATA" <<'PYEOF'
import json, sys
quant, data = sys.argv[1], sys.argv[2]
src, dst = f"/opt/maya/maya-{quant}.json", f"{data}/config/maya-{quant}.json"
cfg = json.load(open(src))
cfg["log"] = f"{data}/config/maya-{quant}.log"
json.dump(cfg, open(dst, "w"), indent=1)
PYEOF
fi

.venv/bin/python - "$cfg" "$CONTEXT" "$PARALLEL" <<'PYEOF'
import json, sys
path, context, parallel = sys.argv[1:4]
cfg = json.load(open(path))
args = cfg.setdefault("args", [])
if context and "--max-context" in args:
    args[args.index("--max-context") + 1] = str(context)
if parallel:
    if "--parallel" in args:
        args[args.index("--parallel") + 1] = str(parallel)
    else:
        args += ["--parallel", str(parallel)]
json.dump(cfg, open(path, "w"), indent=1)
PYEOF

set -- --engine strata --config "$cfg" --host "$HOST" --port "$PORT"
if [ -n "$API_KEY" ]; then set -- "$@" --api-key "$API_KEY"; fi
exec .venv/bin/python serve/server.py "$@"
