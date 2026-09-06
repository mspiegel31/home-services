# LiteLLM Proxy

LiteLLM AI Gateway deployed via Docker Compose with Postgres backend.

## Stack pattern

- `git-sync` sparsely checks out `services/litellm` into the Docker-managed `litellm-config` volume.
- LiteLLM reads the synced config at `/config/current/services/litellm/config.yaml`.
- Postgres data lives on big NVMe at `/mnt/models/litellm/postgres`.
- Valkey (Redis-compatible) data lives on big NVMe at `/mnt/models/litellm/valkey`.
- Admin UI at `http://<host>:4000/ui` — login with `LITELLM_MASTER_KEY`.

## Upstream routing

LiteLLM is the auth, routing, and subscription layer. Every `model_list` entry's
`api_base` points at the llama-swap router (`http://192.168.1.98:11437/v1`), which
selects the GPU backend; LiteLLM presents `LLAMA_SWAP_API_KEY` for each such call.
Client model names match the llama-swap served model ids.

Gotchas that break routing silently:
- `api_base` must keep the `/v1` suffix — llama-swap serves the OpenAI API only
  under `/v1` (root `/chat/completions` 404s), and LiteLLM appends `chat/completions`
  to `api_base` verbatim.
- Each entry needs `custom_llm_provider: openai` — the bare llama-swap model ids
  carry no provider prefix, so LiteLLM's router cannot create a deployment
  without an explicit provider (symptom: "LLM Provider NOT provided" at startup,
  "no healthy deployments" at request time, gateway otherwise looks healthy).

Model capability + reasoning/thinking metadata is authored in `model_info` and surfaced
through LiteLLM discovery endpoints, so Oh My Pi (and any OpenAI client) learns context,
the reasoning-effort ladder, and vision flags without per-workstation overrides.

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

## Qwen3 thinking policy

`custom_callbacks.py` translates public thinking controls for the whole
qwen3 reasoning-parser family the stack serves before LiteLLM forwards
requests. The policy covers Qwen3.8 (`qwen3.8-27b-fp8`,
`-nvfp4-bf16-lmhead`, `-nvfp4-bf16-lmhead-sglang`, `-ninfer`) and the
Ornith checkpoint (`ornith-1.5-9b-nvfp4`).

The SGLang Qwen3.8 deployment declares `custom_llm_provider: hosted_vllm`.
LiteLLM discovery therefore directs OMP to Chat Completions, where explicit
thinking toggles and effort tiers remain available to this callback. No
client-side transport or compatibility override is required.

- `reasoning_effort` `none`/`off` -> `chat_template_kwargs.enable_thinking=false`
- `minimal`/`low` -> `enable_thinking=true`, `reasoning_effort=low`
- `medium` -> `enable_thinking=true`, `reasoning_effort=medium`
- Qwen3.8 `high`/`xhigh`/`max` -> `enable_thinking=true`, `reasoning_effort=xhigh`
- other qwen models preserve their requested effort tier
- zero `thinking_token_budget` -> `enable_thinking=false`
- positive `thinking_token_budget` -> `enable_thinking=true`
- explicit `enable_thinking` wins over effort
- Chat Completions requests with no explicit controls leave the template default
- when the resolved state is thinking-off, any top-level `reasoning_effort` is
  stripped so vLLM's effort->thinking auto-injection cannot re-arm it

The callback is registered in `litellm_settings.callbacks` as
`custom_callbacks.qwen_thinking_policy` and lives beside `config.yaml`,
so git-sync already delivers it to `/config/current/services/litellm/`.

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
