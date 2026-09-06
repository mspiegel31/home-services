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
qwen3 reasoning-parser family before LiteLLM forwards requests. The policy
covers Qwen3.8 (`qwen3.8-27b-fp8`, `-nvfp4-bf16-lmhead`,
`-nvfp4-bf16-lmhead-sglang`, `-ninfer`) and the Ornith checkpoint
(`ornith-1.5-9b-nvfp4`). NInfer has a separate wire-compatibility branch because
it accepts top-level Chat Completions effort but not nested effort, and it
intentionally omits Responses API summaries and encrypted reasoning output.

Module structure: `QwenRequestAdapter` (the registered `CustomLogger` pre-call
hook) dispatches to `NInferResponsesPolicy` (Responses request sanitizing) and
`QwenChatCompletionPolicy` (chat-template control translation). Recognized
models are the `QwenModel` enum with per-model `ModelCapabilities`; client
controls are parsed into a `ThinkingControls` dataclass before any mutation.
The hook boundary uses LiteLLM's own types (`UserAPIKeyAuth`, `DualCache`,
`CallTypesLiteral`) under `TYPE_CHECKING`; the only runtime LiteLLM import is
`CustomLogger`, so the stdlib test stub still works.
Do not enable postponed annotations in this module: LiteLLM executes callback
files without adding their module object to `sys.modules`, while Python
dataclasses resolve postponed annotations through that registry. Keep the three
type-only hook annotations quoted instead.


The vLLM and SGLang Qwen3.8 deployments declare
`custom_llm_provider: hosted_vllm`. LiteLLM discovery therefore directs OMP to
Chat Completions, where explicit thinking toggles and effort tiers remain
available to this callback. No client-side transport or compatibility override
is required.

- `reasoning_effort` `none`/`off` -> `chat_template_kwargs.enable_thinking=false`
- vLLM/SGLang `minimal`/`low` -> `enable_thinking=true`, nested `reasoning_effort=low`
- vLLM/SGLang `medium` -> `enable_thinking=true`, nested `reasoning_effort=medium`
- vLLM/SGLang Qwen3.8 `high`/`xhigh`/`max` -> nested `reasoning_effort=xhigh`
- NInfer Chat Completions keeps `reasoning_effort` top-level and adds only
  `chat_template_kwargs.enable_thinking`
- NInfer Responses requests drop `reasoning.summary` and
  `include: ["reasoning.encrypted_content"]`; NInfer returns raw reasoning text
  but cannot produce either requested representation
- other qwen models preserve their requested effort tier
- zero `thinking_token_budget` -> `enable_thinking=false`
- positive `thinking_token_budget` -> `enable_thinking=true`
- explicit `enable_thinking` wins over effort
- Chat Completions requests with no explicit controls leave the template default
- when the resolved state is thinking-off, any top-level `reasoning_effort` is
  stripped so the backend cannot re-arm it

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
