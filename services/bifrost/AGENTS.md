# Bifrost AI Gateway

Bifrost (maximhq/bifrost) AI gateway deployed via Docker Compose. Presents an
OpenAI-compatible API in front of the llama-swap router, with per-client
virtual keys, a dashboard, and MCP tool aggregation (MCP unused here).

## Stack pattern

- Bifrost only reads `<app-dir>/config.json` (a file), and the image ships
  `/app/data` as a directory that also owns `config.db`/`logs.db` — a ro file
  mount cannot overlay it. The container `command` therefore stages the
  git-synced config into `/app/data/config.json` at boot, and a 20s watcher
  re-stages it and restarts the gateway when the source file changes.
- Dashboard at `http://<ai-box>:8080` — first-time setup uses
  `BIFROST_SETUP_TOKEN`; dashboard/API setup is separate from inference
  endpoints.
- OpenAI endpoint: `http://<ai-box>:8080/v1`.

## Upstream routing

Every request goes to the llama-swap router with `LLAMA_SWAP_API_KEY` (same
key the litellm stack uses). Model names pass through unchanged — Bifrost's
`models: ["*"]` whitelist delegates model selection to llama-swap, which owns
model lifecycle on the GPU box.

Gotchas:

- `base_url` must NOT include the `/v1` suffix — the OpenAI provider calls
  `<base_url>/v1/...` paths itself, so a `/v1`-bearing base would produce
  `/v1/v1/...` (404).
- `BIFROST_ENCRYPTION_KEY` encrypts the config store and must stay stable
  across restarts/upgrades/restores (rotating it loses stored keys).
- The staged copy in `/app/data` overwrites on every boot, so git is always
  the source of truth. Dashboard edits persist in the sqlite store inside
  `bifrost-data`; they take effect for the current process, but any
  config.json change from git (re-stage) re-syncs them on the next start.

## Config management

- `config.json` is delivered by git-sync; `env.VAR` references resolve from
  the container environment (Portainer-injected), so secrets never land in
  the repo.
- `config.json` changes in git take effect within ~50s without a redeploy:
  git-sync polls every 30s, the watcher re-stages and restarts the gateway
  every 20s.
- `BIFROST_ENCRYPTION_KEY`, `BIFROST_SETUP_TOKEN`, `LLAMA_SWAP_API_KEY` are
  set in the Portainer stack env UI — never commit.

## Client logging

`client.enable_logging: true` + `client.disable_content_logging: true` logs
every request's metadata (model, tokens, latency, virtual key, status) while
excluding inputs/outputs. `logs_store` is set explicitly to sqlite at
`/app/data/logs.db` (confirmed against the live schema's root `logs_store`
field); the dashboard shows metadata only.

## Compatibility limits vs. the litellm path

`client.compat` set to all `false` prevents Bifrost-side conversion and
parameter dropping only. It does NOT replicate
`services/litellm/custom_callbacks.py`, which actively transforms fields
(e.g. reasoning-effort tiers into each local model's chat-template contract).
Consequences for clients moving through Bifrost:

- Custom unknown request fields (e.g. `thinking_token_budget`) are not
  forwarded by default; future clients must send the
  `x-bf-passthrough-extra-params: true` header for such fields. The OMP
  change to send it is deferred, and `~/.omp` remains untouched.
- Binary-stripping models (those that must not receive reasoning effort)
  may need a future llama-swap-side filter; llama-swap is not modified now.

## Model compatibility groups

The 14 llama-swap chat lanes (names pass through unchanged; Bifrost's
wildcard whitelist must cover all of them without aliasing):
`muse-glimmer-30b`, `muse-glimmer-30b-nvidia-nvfp4`, `gemma-4-31b`,
`qwen3.8-27b-nvfp4`, `qwen3.8-27b-nvfp4-bf16-lmhead`,
`swift-qwen3.8-27b-nvfp4`, `qwen3.8-27b-quasar-nvfp4`,
`qwen3.8-27b-nvfp4-bf16-lmhead-sglang`, `qwen3.8-27b-ninfer`,
`laguna-xs-2.1`, `qwen3.8-27b-fp8`, `nemotron-3.5-lightning`,
`ornith-1.5-9b-nvfp4`, `ornith-1.5-35b-a3b-nvfp4`.

Reasoning-effort contracts (as advertised in
`services/litellm/config.yaml` model_info):

- Muse lanes: 4 tiers — `low`/`medium`/`high`/`xhigh`.
- Qwen lanes: 3 tiers — `low`/`medium`/`xhigh`; `qwen3.8-27b-fp8`
  advertises `low` only.
- Binary-thinking lanes (Gemma 4, Laguna, both Ornith): must NOT receive
  `reasoning_effort` — their templates take `enable_thinking` only.
- `qwen3.8-27b-ninfer`: requires top-level effort and Chat Completions
  (not the nested thinking-contract form).
- `nemotron-3.5-lightning`: no current effort ladder.

Runtime canaries through Bifrost are deferred solely because this
migration's verification is static-only and must not invoke/start models.
Inference auth is disabled independently of that, to avoid lockout (below).

## Inference auth

`client.enforce_auth_on_inference: false` — inference authentication is
deliberately disabled for this migration to avoid locking out the current
stack before admin/virtual keys exist. The setup token and dashboard auth
remain separate concerns; the inference endpoint is NOT currently
virtual-key-required. Before enabling it, create admin/virtual keys in the
dashboard first.

## Known upstream behavior

Bifrost historically shuffled MCP tool schema keys on its 10-minute tool list
refresh (Go map iteration), which broke vLLM prefix caches on every refresh —
fixed upstream in maximhq/bifrost#7170 (schema keys sorted during conversion).
Irrelevant until MCP aggregation is enabled, but relevant if agent traffic
through Bifrost ever shows periodic cache-busting.
