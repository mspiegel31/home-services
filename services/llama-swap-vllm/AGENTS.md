# llama-swap-vllm

Portainer CE stack: git-sync sidecar + llama-swap router in the upstream
`unified-cuda` image (digest-pinned) + lazily spawned vLLM backend containers
via the Docker socket. Secrets (`LLAMA_SWAP_API_KEY`, `HF_TOKEN`) are injected
by Portainer — never commit them.

## Router image

- `ghcr.io/mostlygeek/llama-swap:unified-cuda@sha256:...` — the `unified-cuda`
  tag is a moving nightly build from llama-swap main HEAD; the digest pin is
  the version control. To upgrade: pull the new digest
  (`docker manifest inspect ghcr.io/mostlygeek/llama-swap:unified-cuda`) and
  update `docker-compose.yml`. `/versions.txt` inside the image lists the
  bundled component revisions.
- The image bundles `vllm-wrapper` (vLLM sleep/wake support). Currently
  unused — sleep/wake is disabled in `config.yaml` pending upstream vLLM fixes
  (garbled output on wake).
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
