# Bifrost AI Gateway

Bifrost (maximhq/bifrost) AI gateway deployed via Docker Compose. Presents an
OpenAI-compatible API in front of the llama-swap router, with per-client
virtual keys, a dashboard, and MCP tool aggregation (MCP unused here).

## Stack pattern

- `git-sync` sparsely checks out `services/bifrost` into the Docker-managed
  `bifrost-config` volume (same pattern as `services/litellm`).
- Bifrost reads the synced `config.json` at `/app/data/config.json` (ro file
  mount on top of the `bifrost-data` named volume).
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
- The ro `config.json` mount means the dashboard cannot rewrite the file; the
  git-synced file is the source of truth. Dashboard edits persist in the
  sqlite store inside `bifrost-data` and shadow `config.json` on next boot —
  keep provider changes in git and redeploy, not in the dashboard.

## Config management

- `config.json` is delivered by git-sync; `env.VAR` references resolve from
  the container environment (Portainer-injected), so secrets never land in
  the repo.
- Changes require a redeploy of the Portainer stack (pull 5 min poll, or
  `StackGitRedeploy`); Bifrost does not hot-reload config.json.
- `BIFROST_ENCRYPTION_KEY`, `BIFROST_SETUP_TOKEN`, `LLAMA_SWAP_API_KEY` are
  set in the Portainer stack env UI — never commit.

## Known upstream behavior

Bifrost historically shuffled MCP tool schema keys on its 10-minute tool list
refresh (Go map iteration), which broke vLLM prefix caches on every refresh —
fixed upstream in maximhq/bifrost#7170 (schema keys sorted during conversion).
Irrelevant until MCP aggregation is enabled, but relevant if agent traffic
through Bifrost ever shows periodic cache-busting.
