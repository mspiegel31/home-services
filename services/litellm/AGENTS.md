# LiteLLM Proxy

LiteLLM AI Gateway deployed via Docker Compose with Postgres backend.

## Stack pattern

- `git-sync` sparsely checks out `services/litellm` into the Docker-managed `litellm-config` volume.
- LiteLLM reads the synced config at `/config/current/services/litellm/config.yaml`.
- Postgres data lives on big NVMe at `/mnt/models/litellm/postgres`.
- The CPU-only `nomic-embed-text-v2-moe` TEI service lives in this stack and
  stays resident independently of llama-swap's GPU lifecycle.
- Valkey (Redis-compatible) data lives on big NVMe at `/mnt/models/litellm/valkey`.
- Admin UI at `http://<host>:4000/ui` — login with `LITELLM_MASTER_KEY`.

## Upstream routing

LiteLLM routes chat models through llama-swap at
`http://192.168.1.98:11437/v1`. The always-resident
`nomic-embed-text-v2-moe` embedding model bypasses llama-swap and reaches the
CPU Text Embeddings Inference container over the shared `litellm` network.
Client model names match their upstream served model ids.

Gotchas that break routing silently:
- `api_base` must keep the `/v1` suffix — llama-swap serves the OpenAI API only
  under `/v1` (root `/chat/completions` 404s), and LiteLLM appends `chat/completions`
  to `api_base` verbatim.
- Each entry needs `custom_llm_provider: openai` or `hosted_vllm` — the bare llama-swap model ids
  carry no provider prefix, so LiteLLM's router cannot create a deployment
  without an explicit provider (symptom: "LLM Provider NOT provided" at startup,
  "no healthy deployments" at request time, gateway otherwise looks healthy).
  Prefer `hosted_vllm`: LiteLLM discovery then directs OMP to Chat Completions
  and synthesizes the `thinking` block OMP's UI requires (see Qwen3 thinking policy below).

Model capability + reasoning/thinking metadata is authored in `model_info` and surfaced
through LiteLLM discovery endpoints, so Oh My Pi (and any OpenAI client) learns context,
the reasoning-effort ladder, and vision flags without per-workstation overrides.

Client API keys need `allowed_routes` that include the discovery routes, not
just `llm_api_routes`. OMP's `discovery.type: litellm` probes `/v2/model/info`
(rich catalog) and falls back to `/v1/models` when it 403s. A key without the
route therefore still serves chat, but OMP loses every `model_info` field
(`reasoning_effort` ladder, `reasoning`, context window), so its thinking
control degrades to a binary toggle and the effort ladder disappears from the
`/models` picker. Grant the routes:

```
POST /key/update   # master key
{"key": "<key>", "allowed_routes": ["llm_api_routes", "/v2/model/info",
  "/v1/models", "/model/info", "/model_group/info"]}
```

Symptom is silent: the model works, only the effort controls stop being
respected. Verify with `curl <key> /v2/model/info` → 200.

## Config management

LiteLLM supports multiple config sources:
1. Config file (highest priority): mounted from git-sync at `/config/current/services/litellm/config.yaml`.
2. Environment variables override via `os.environ/` syntax in YAML.
3. Native S3/GCS config loading: set `LITELLM_CONFIG_BUCKET_TYPE/NAME/OBJECT_KEY` env vars to load config from a bucket. This is the Litellm-provided alternative to git-sync and is preferred for large-scale deployments.

For home-services consistency, git-sync is used here. Switch to S3 bucket config by:
- Setting `LITELLM_CONFIG_BUCKET_TYPE`, `LITELLM_CONFIG_BUCKET_NAME`, `LITELLM_CONFIG_BUCKET_OBJECT_KEY`
- Removing the `git-sync` service and volume mount, and passing `--config` with a bucket path or omitting config file entirely.

## Portainer notes

- Do not use `env_file`; declare `${VAR}` explicitly as per repo policy.
- Set in Portainer UI:
  - `LITELLM_MASTER_KEY` — Admin UI password
  - `LITELLM_SALT_KEY` — encryption salt for provider keys
  - `LITELLM_POSTGRES_PASSWORD` — Postgres password
  - Provider API keys as needed (e.g., `OPENAI_API_KEY`)
  - `LLAMA_SWAP_API_KEY` — API key presented to the llama-swap router (matches the value configured in the llama-swap-vllm stack)

## Local reasoning-model thinking policy

`custom_callbacks.py` translates public thinking controls before LiteLLM
forwards Chat Completions requests. It handles Qwen3.8 FP8, both Flash Next
NVFP4 routes, and both Swift 1.5 27B routes with nested three-tier effort.
Both Flash Next backends mount the repo's Froggeric template from the
llama-swap git-sync volume. Swift 1.5 requests without thinking controls
receive an explicit xhigh default; base Qwen3.8 routes leave the Froggeric
medium default intact.

The Swift Flash Next serving route currently trials stock vLLM 0.30.0 with
CPU PLE and expert-weight offload. Unlike the LIL base Flash Next route, it
starts without MTP or RAM KV offload; startup and GPU fit remain unverified.

`LocalReasoningRequestAdapter` dispatches to `ChatTemplateThinkingPolicy`.
Recognized models are listed in `LocalReasoningModel`; client controls are
parsed into `ThinkingControls` before mutation. The only runtime LiteLLM
import is `CustomLogger`. Keep type-only hook annotations
quoted: LiteLLM loads callback files without registering the module in
`sys.modules`, which breaks dataclass annotation resolution under postponed
annotations.

All local chat deployments declare `custom_llm_provider: hosted_vllm`. LiteLLM
discovery therefore directs OMP to Chat Completions, where its thinking controls
reach this callback. The CPU embedding deployment uses the same provider for
OpenAI-compatible `/v1/embeddings`; callback payload detection leaves it unchanged.

- The local Qwen3.8 and Swift 1.5 routes map `minimal`/`low` to nested effort
  `low`, `medium` to `medium`, and `high`/`xhigh`/`max` to `xhigh`.
- zero `thinking_token_budget` -> `enable_thinking=false`
- positive `thinking_token_budget` -> `enable_thinking=true`
- explicit `enable_thinking` wins over effort
- Chat Completions without explicit controls leave base Qwen3.8 template
  defaults intact; Swift 1.5 receives xhigh.
- when the resolved state is thinking-off, any top-level `reasoning_effort` is
  stripped so the backend cannot re-arm it

The callback is registered in `litellm_settings.callbacks` as
`custom_callbacks.local_thinking_policy` and lives beside `config.yaml`, so
git-sync already delivers it to `/config/current/services/litellm/`.

`test_custom_callbacks.py` is a stdlib-only smoke suite (no pytest, no
LiteLLM needed — it stubs the import): `python3 test_custom_callbacks.py`.

After a policy update, restart the `litellm` service to reload the module.

## Production hardening

- Pin image tag instead of `main-stable` for production.
- Valkey backs cross-worker rate limits, spend tracking, and coordination via
  `general_settings.coordination_redis` in the config. A bare `REDIS_URL` env var
  alone does NOT enable it — that env fallback only runs when
  `litellm_settings.cache: true`, which would also turn on response caching.
- Enable TLS termination at reverse proxy.
- See LiteLLM Production Deployment guide for Helm/K8s recommendations.
