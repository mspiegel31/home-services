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
  `BIFROST_SETUP_TOKEN`, then Bearer tokens/virtual keys for API + MCP calls.
- OpenAI endpoint: `http://<ai-box>:8080/v1`,
  `Authorization: Bearer <virtual-key>`.

## Upstream routing

Every request goes to the llama-swap router at
`http://192.168.1.98:11437/v1` with `LLAMA_SWAP_API_KEY` (same key the
litellm stack uses). Model names pass through unchanged — Bifrost's
`models: ["*"]` whitelist delegates model selection to llama-swap, which owns
the vLLM backend fan-out.

Gotchas:

- `base_url` must keep the `/v1` suffix — llama-swap serves the OpenAI API
  only under `/v1` (root `/chat/completions` 404s).
- Bifrost has no master key: `BIFROST_ENCRYPTION_KEY` encrypts the config
  store and must stay stable across restarts/upgrades/restores (rotating it
  loses stored keys). Clients authenticate with virtual keys created in the
  dashboard, not with the setup token.
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

## Known upstream behavior

Bifrost historically shuffled MCP tool schema keys on its 10-minute tool list
refresh (Go map iteration), which broke vLLM prefix caches on every refresh —
fixed upstream in maximhq/bifrost#7170 (schema keys sorted during conversion).
Irrelevant until MCP aggregation is enabled, but relevant if agent traffic
through Bifrost ever shows periodic cache-busting.
