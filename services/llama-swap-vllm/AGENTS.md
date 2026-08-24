# llama-swap-vllm

llama-swap runs as a host systemd service. A git-sync container (Portainer
stack) pulls this repo into `/home/cloud/llama-swap`; llama-swap reads its
config from the bind-mounted directory and watches for changes via
`--watch-config`. vLLM backend containers are spawned lazily by llama-swap
through the host Docker CLI — they are NOT Compose-managed services.

Secrets (`LLAMA_SWAP_API_KEY`, `HF_TOKEN`) live in `/etc/llama-swap/env`
(EnvironmentFile for the systemd unit) — never commit them.

## Files

- `install.sh` — installs the llama-swap binary (+ optional vllm-wrapper),
  creates `/etc/llama-swap/env`, and enables the systemd service. Run with
  sudo on the host.
- `llama-swap.service` — systemd unit. Listens on `0.0.0.0:11437`.
- `env.example` — template for `/etc/llama-swap/env`.
- `docker-compose.yml` — Portainer stack with only the git-sync sidecar.
  Bind-mounts `/home/cloud/llama-swap` for the config checkout.
- `config.yaml` — llama-swap model definitions. Read by the host binary via
  the git-sync bind mount.

## Architecture

```
git-sync container → /home/cloud/llama-swap/current/ (bind mount)
                          ↓
llama-swap (host systemd) → reads config.yaml (--watch-config)
                          ↓
                    docker run -p ${PORT}:8000 vllm/vllm-openai:...
                          ↓
                    proxy → http://localhost:${PORT}
```

Each model uses the `${PORT}` macro: llama-swap assigns a unique port
(starting at `startPort: 5800`), publishes it via `-p ${PORT}:8000` in the
docker run command, and proxies to `http://localhost:${PORT}` (the default
when `proxy:` is omitted).

## `config.yaml` rules

- **Never add `--trust-remote-code` to a model's `cmd`.** Every backend must
  load without executing Python code from its model repository.
- `macros` (global and per-model) must be a YAML **mapping** (`NAME: value`),
  never a list of `{name, value}` — llama-swap rejects non-mapping blocks
  with "macros must be a mapping".
- `--enable-prefix-caching` lives in the `VLLM_COMMON` macro (all backends);
  do not duplicate it per model.
- Backends publish their port to the host via `-p ${PORT}:8000` in
  `DOCKER_PREFIX`; `proxy:` is omitted (defaults to
  `http://localhost:${PORT}`). Never use Docker network DNS names — the
  router runs on the host, not inside a Docker network.

## Sleep/wake status

Sleep/wake is disabled (cold swap via `docker stop`/`docker run`). The
garbled output on wake was caused by vLLM bugs — FP8 KV cache scale factors
not reinitialized on wake (vllm#25800, PR #28783) and prefix cache not
resetting (vllm#16234) — not by containerization. Re-enable when our pinned
vLLM image includes both fixes. `vllm-wrapper` is installed if Go is present
on the host; it enables sleep/wake without code changes to `config.yaml`.
