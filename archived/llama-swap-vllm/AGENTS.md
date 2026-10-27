# llama-swap-vllm

Portainer CE stack: git-sync sidecar + llama-swap router in a derived image
(`unified-cuda` + `docker.io` CLI) + lazily spawned vLLM backend containers
via the Docker socket. Secrets (`LLAMA_SWAP_API_KEY`, `HF_TOKEN`) are injected
by Portainer — never commit them.

- `ghcr.io/mspiegel31/llama-swap-vllm:latest` — derived from
  `ghcr.io/mostlygeek/llama-swap:unified-cuda` with `docker.io` added so the
  router can spawn backend containers via the Docker socket. The base tag is
  a moving nightly from llama-swap main HEAD; rebuild via CI to pick up base
  updates. Check `/versions.txt` inside the container for bundled revisions.
- The base image bundles `vllm-wrapper` (vLLM sleep/wake support). Currently
  unused — sleep/wake is disabled in `config.yaml` pending upstream vLLM fixes.
- We do not run the image's own llama.cpp/whisper/sd tooling: all backends are
  vLLM containers spawned through the socket. The image's CUDA runtime is
  12.9.1; that only matters if we ever load a model into the router image
  itself (host driver is newer, CUDA 13.2-compat, so that would work too).
- GPU stats (temperature, power, utilization, memory in `/metrics` and the
  UI) come from `nvidia-smi` inside the router container. The `deploy` GPU
  reservation in the compose is required for that; it allocates no VRAM.

## `config.yaml` rules

- **Never add `--trust-remote-code` to a model's `cmd`.** Every backend must
  load without executing Python code from its model repository.
- `macros` (global and per-model) must be a YAML **mapping** (`NAME: value`),
  never a list of `{name, value}` — llama-swap v250 rejects non-mapping
  blocks with "macros must be a mapping".
- `--enable-prefix-caching` lives in the `VLLM_COMMON` macro (all backends);
  do not duplicate it per model.
- Backends are addressed by docker network DNS
  (`proxy: http://<container-name>:8000`); the router container shares the
  `llama-swap-vllm-backend` network. Never proxy via host loopback ports.
- The router reads `config.yaml` and every `models/*.yaml` **once at startup**:
  a merged change to a model's `cmd` is not live until the stack is redeployed
  (or `docker restart llama-swap-vllm`). git-sync updating the checkout within
  30s is not enough, and there is no reload endpoint (`/api/reload`,
  `/api/restart`, `/api/admin/*` are 404; `/api/version` and `/api/profiles`
  are keyed and read-only). `-watch-config` is deliberately NOT set: with it,
  every 30s sync of a changed config reloads the router and can unload a lane
  someone is using mid-session. So: **a lane change ships as a stack redeploy**,
  and a lane still running an older `cmd` is expected until then.

## Configuration tips
1. it's always worth checking https://recipes.vllm.ai/ to see if there are tips and tricks if we're using vllm as the engine

## Amazing prior art
1. for vllm, recipes and tips for models can be found in https://recipes.vllm.ai/

## Strata lanes
- Lane env contract (each start, `images/strata/merge_args.py` writes these
  into `/mnt/more-models/strata/config/strata-*.json`): `PARALLEL` ->
  `parallel`, `STRATA_VRAM_RESERVE_MIB` -> `--vram-reserve-mib`,
  `STRATA_PLE_IO` -> `--ple-io`, `STRATA_VISION_MMPROJ` -> `--vision` + the
  vision block. Never hand-edit those keys in the volume json: set the lane
  env instead.
- Sizing rule: post-load free VRAM (engine log line `strata serve: N MiB of
  VRAM free with everything loaded`) must be >= (2^PARALLEL - 1) x ~9 MiB x
  1.5, i.e. >= 850 MiB at 6 slots — the verify path caches one CUDA graph
  pair per busy-slot subset and never evicts. Full diagnosis: merge_args.py's
  docstring. Crash signature `verify: batch instantiate: out of memory` ->
  raise STRATA_VRAM_RESERVE_MIB or lower PARALLEL.
- Graphs captured since the last engine start (must stay <= 2^PARALLEL - 1):
  `docker exec <lane> awk '/PCIe probe/{b=0} /captured the batch window/{b++} END{print b}' /opt/strata/strata-<tag>.log`