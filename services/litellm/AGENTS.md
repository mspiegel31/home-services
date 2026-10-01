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
1. Config file (highest priority): mounted from git-sync at `/config/current/services/litellm/config.yaml`. Chat-model deployments live in `models/<model-id>.yaml`, pulled in via the `include` directive in `config.yaml` (explicit file list, no glob; `model_list` concatenates in listed order). LiteLLM `include` files are parsed separately, so YAML anchors/merge keys do not cross file boundaries — model files are fully self-contained.
2. Environment variables override via `os.environ/` syntax in YAML.

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
forwards Chat Completions requests. It handles the registered Qwen3.8 and
Swift 1.5 routes, including the RedHat and Unsloth NVFP4 lanes, with
nested three-tier effort.
Both Flash Next backends mount the repo's Froggeric template from the
llama-swap git-sync volume. Swift 1.5 requests without thinking controls
receive an explicit xhigh default; base Qwen3.8 routes leave the Froggeric
medium default intact.

The RedHat NVFP4 lane runs DSpark7 with prefix caching disabled. The
base-weights FP8 lane runs the checkpoint's native MTP3 with prefix caching on,
after DSpark7 measured level with it on prose and agent traffic
(services/llama-swap-vllm/BENCHMARKS.md), and keeps the v0.30.0 build's #50729
copy-race fix; the Mamba checkpoint reuse path (#57128) is still open and
speculation-gated, so FP8 prefix reuse is canary-checked, not assumed correct,
and disabling it is one flag away. The Unsloth lane also uses native MTP3 with
prefix caching and Mamba `align` mode. All share the hybrid GDN architecture
involved in the prior reused-prefix corruption; a drafter or weight-precision
change does not prove cache correctness.
When evaluating prefix reuse, check the installed vLLM build against
[vllm#53912](https://github.com/vllm-project/vllm/issues/53912) and compare
cold versus reused-prefix outputs with confirmed cache hits. A successful
no-prefix-cache smoke run does not validate automatic prefix caching.

OMP overrides for both lanes explicitly set `supportsTools: true` and
`compat.supportsToolChoice: true`. With `tools.format: auto`, this preserves
native tool calls for vLLM's `qwen3_xml` parser instead of an in-band dialect.

Swift Flash Next disables the LIL profile's default MTP3: its draft loader
exhausts the 72 GB GPU during online NVFP4 weight processing. Base Qwen Flash
Next retains MTP3. Swift GPU fit without the drafter remains unverified.

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
