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

## Sleep/wake status

Sleep/wake is disabled (cold swap via `docker stop`/`docker run`). The
garbled output on wake was caused by vLLM bugs — FP8 KV cache scale factors
not reinitialized on wake (vllm#25800, PR #28783) and prefix cache not
resetting (vllm#16234) — not by containerization. Re-enable when our pinned
vLLM image includes both fixes.
