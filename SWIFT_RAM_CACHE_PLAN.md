# Prepare Swift RAM prefix caching without changing the live server

## Context
Prepare an opt-in LMCache RAM tier for long multi-turn OMP conversations and inactive sessions that later resume. The cache must survive removal/recreation of Swift's vLLM container; host-reboot persistence is unnecessary. Preserve the public model ID `swift-qwen3.8-27b-nvfp4`, vision, tool calling, native MTP, and the current 90% GPU budget; defer Nemotron co-residency. This execution prepares build/configuration artifacts and runnable checks only: the user explicitly declined live testing, deployment, model restarts, and performance claims before a later maintenance window.

### Moving pieces: two containers, one reusable image

| Component | Where it runs | Responsibility | Lifetime |
|---|---|---|---|
| llama-swap router | Existing Compose service | Routes requests and launches/stops Swift | Independent of individual model loads |
| LMCache server | New sibling Compose service, `lmcache-swift`, in the same llama-swap stack | Owns the reusable RAM cache | Survives Swift unloads; loses RAM contents if this service restarts |
| Swift vLLM engine and LMCache connector | The model container launched by llama-swap | Runs inference; connector libraries transfer KV tensors to/from the server | Removed and recreated during model switching |

The connector is a Python/native dependency inside vLLM, not a second server launched inside the vLLM container. The LMCache server runs in its own container. There is no supervisor or shell script launching both services together; vLLM retains its normal internal worker processes.

Build one candidate image containing the existing Swift runtime plus LMCache. Use it in two containers with different entrypoints: the normal vLLM entrypoint for Swift, and `lmcache server` for the cache service. Sharing an image does not couple container lifetimes. It keeps the client/server package versions aligned without changing the pinned inference runtime.

The sidecar therefore solves cache ownership and lifetime, but does not remove the need for LMCache connector code in the vLLM image. An upstream standalone server image alone cannot supply that code to another container. This plan retains the pinned custom candidate rather than introducing an unverified upstream image pairing.

Prepare the sidecar as an **opt-in Compose override of the existing stack**, not a separate Portainer stack. It remains inactive until explicitly included at deployment. A whole-stack shutdown also stops the sidecar and clears the RAM cache; ordinary Swift unloads do not.

## Evidence and decisions

- `services/llama-swap-vllm/config.yaml` defines the Swift model, `DOCKER_PREFIX`, `VLLM_COMMON`, and routing matrix. Swift uses `ukisai/Swift-Qwen3.8-27B-NVFP4`, `--kv-cache-dtype fp8_e4m3`, native MTP with 3 speculative tokens, fastokens, the Froggeric v22.5 template, and a FlashInfer FP8 linear-kernel workaround. Preserve these settings.
- The running vLLM 0.29.0 engine logged a 1600-token unified block, 38.72 GiB cache capacity, 1,092,510 aggregate cached tokens, and full 262144 context. Its startup scheduler had 8192 batched tokens, while the currently read repo specifies 4096. The candidate must derive from one explicit baseline configuration and compare against that same baseline; do not mix these settings during A/B measurement. A repo comment's 2048-token block and LMCache's stock-model example of 784 are not authoritative for this Swift checkpoint.
- Read-only host measurements: 49 GiB RAM visible to Linux, 36 GiB available, PCIe Gen3 x16. These are snapshots, not peak guarantees. Choose a 16 GiB maximum RAM cache, initially allocating 4 GiB. LMCache's pinned `lmcache/v1/distributed/config.py` multiplies its `*-size-gb` arguments by `1 << 30`; units are GiB despite the flag names. Its default initial 20 GiB is clamped to the maximum, but explicitly selecting 4 avoids allocating the full cap at startup.
- `services/llama-swap-vllm/docker-compose.yml` uses git-sync and deliberate router restart/redeploy, without `--watch-config`. Backend model containers use `docker run --rm`; they do not own the LMCache service.
- Native vLLM 0.29.0 exposes `--kv-offloading-size` and `--kv-offloading-backend native`. Its CPU tier is process-local: [SharedOffloadRegion](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/v1/kv_offload/cpu/shared_offload_region.py) unlinks the shared region after mapping and the kernel reclaims it when workers exit. Native RAM caching therefore fails the required lifecycle. Native filesystem secondary tiers are a different design and are not part of this RAM-only preparation.
- Choose LMCache multiprocess mode with an independently managed server. Pin source revision `05a013b29da78cf2321b9b46ec5039dde2fb0bb0` (v0.5.5). Read source: `requirements/build.txt`, `requirements/common.txt`, `pyproject.toml`, `lmcache/integration/vllm/lmcache_mp_connector.py`, and `lmcache_mp_metadata.py`. The connector subclasses `SupportsHMA`, supports separate recurrent groups, and schedules STORE operations for complete computed chunks during prefill and subsequent cached-request steps. Non-lazy request completion uses the delayed-free path. Partial tails and missing recurrent snapshots are recomputed; do not promise every generated token will survive unload.
- Use eager cache stores (`lmcache.mp.lazy_offload=false`). Eviction-only lazy offload can leave a recently used prefix solely in VRAM when the engine stops. Keep LMCache autostart disabled; a child owned by vLLM does not provide independent lifetime.
- Active image digest, read from both the running container and local image metadata: `ghcr.io/mspiegel31/vllm-fastokens@sha256:43c2352ded4e132d18fda6af2adabc3052afd660ebbd08bc9027ef8f0ecf7278`. Derive the candidate from this immutable image. Do not modify the existing Dockerfile, shared latest tag, vLLM, PyTorch, model checkpoint, or template.
- Exact Swift NVFP4 + FP8 KV + MTP + external cache + vision correctness and performance are **unverified**. [LMCache hybrid documentation](https://docs.lmcache.ai/mp/hybrid_models.html) validates stock text cases, not this exact combination. [LMCache #4674](https://github.com/LMCache/LMCache/issues/4674) documents silent corruption in related interleaved-session configurations. [vLLM #54163](https://github.com/vllm-project/vllm/pull/54163) primarily changes DFlash/DSpark behavior and explicitly preserves MTP semantics; do not blindly apply it to Swift or claim its presence proves safety. No upstream patch or MTP removal is authorized by this plan.

## Approach

### 1. Package the connector without launching another service inside vLLM

Create `images/vllm-fastokens/Dockerfile.lmcache`. No equivalent candidate recipe exists; the existing Dockerfile is the production image and must remain unchanged. Base the new recipe on the immutable fastokens image above. Label the LMCache source revision in the image.

Build LMCache from the pinned source against the base image's installed PyTorch using `--no-build-isolation`, with `TORCH_CUDA_ARCH_LIST=12.0` and `MAX_JOBS=4`. Install the pinned source's build requirements and runtime dependencies under constraints preserving the base versions of `vllm`, `torch`, `torchvision`, `torchaudio` when installed, `triton`, `transformers`, `fastokens`, FlashInfer distributions, and NVIDIA CUDA-runtime packages. Capture those package versions with `importlib.metadata` during the build, before dependency installation; enforce equality afterward. Use the pinned GitHub archive, with `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LMCACHE=0.5.5` for archive builds. Do not install the generic prebuilt wheel blindly: its pyproject builds against torch 2.13.0, which may not match the base.

A resolver/build incompatibility must fail the candidate build with the actual conflict; do not relax the core constraints or silently upgrade the engine. Run import/ABI checks and `pip check` inside the built image without allocating a GPU. Preserve the existing vLLM image entrypoint so the image can serve Swift. The cache compose file overrides the entrypoint for its server process.

Use local tag `swift-ram-cache:vllm-0.29.0-lmcache-0.5.5`. Do not change `.github/workflows/build-images.yml`: it discovers only `images/*/Dockerfile`, so this alternate recipe is deliberately not auto-published. No push, remote build, or active-host installation is part of preparation.

### 2. Add the RAM-cache sidecar to the existing stack

Create `services/llama-swap-vllm/compose.lmcache.yml` as an opt-in override of `docker-compose.yml`, with no separate project name or network declaration. No existing independent KV-cache service exists. Add only service `lmcache-swift`, container name `lmcache-swift`, using the candidate image and the existing `backend` network. Do not change the router's dependencies: other models must remain usable without starting this optional cache service. Check sidecar health before explicitly loading the cache-enabled Swift configuration.

Use `entrypoint: ["lmcache"]` and these exact server arguments:

```text
server --host 0.0.0.0 --port 5555
--http-host 0.0.0.0 --http-port 8080
--prometheus-port 9090
--chunk-size 1600 --separate-object-groups
--l1-size-gb 16 --l1-use-lazy --l1-init-size-gb 4
--eviction-policy LRU
--no-isolated-ipc
```

Specify `ipc: host`, GPU reservation following the existing compose device pattern, `ulimits.memlock: -1`, `mem_limit: 20g`, `memswap_limit: 20g`, and `restart: unless-stopped`. Explicitly disabling isolated IPC on both ends avoids relying on version-dependent defaults; Swift already uses host IPC and `expandable_segments:False`. Set `LMCACHE_TRACK_USAGE=false`. Add a health check using Python's standard-library HTTP client against `http://127.0.0.1:8080/healthcheck`, with 30-second interval, 5-second timeout, 5 retries, 120-second start period.

Publish no host ports. Mount no Docker socket, checkpoint directory, credentials, or persistent cache volume into this service. Use no `env_file`, L2 backend, Redis, disk offload, compression, or CacheBlend. This cache is disposable RAM: server restart or LRU eviction may cause a cache miss and recomputation, but must not lose conversation text stored by OMP.

The service's GPU context and transfer work can consume some VRAM; it is not a zero-VRAM component. This is measured in the later runtime gates, not compensated by shrinking Swift's budget now. Always merge this override with the production compose file; it is not a standalone stack. A missing candidate image causes normal compose failure rather than pulling an unrelated image.

### 3. Generate opt-in router configurations from the existing source

Create `scripts/prepare_swift_ram_cache.py`, a small Python CLI using PyYAML (declare PEP 723 dependency `pyyaml>=6,<7`). No existing script renders a cache candidate. Reuse the existing full router YAML as input rather than checking in a second manually maintained model catalogue.

CLI:

```text
python scripts/prepare_swift_ram_cache.py --source PATH --output-dir DIRECTORY
```

Require an explicit output directory, reject output within `services/`, refuse to overwrite existing outputs, and reject input lacking the exact Swift model or already containing a KV connector/offload configuration for it. Parse YAML structurally. Reject a baseline with a different checkpoint, MTP method/count, FP8 KV dtype, or GPU budget than the selected contract; report the differing field rather than rewriting it. Keep secrets as `${env.*}` references and never print resolved secret values.

Write these artifacts to the output directory:

1. `baseline.yaml`: a structural copy with Swift's `VLLM_IMAGE` macro pinned to the immutable base digest above, all other model/routing values unchanged.
2. `candidate.yaml`: derived from baseline; change only Swift's image macro to the candidate tag and append explicit `--mamba-cache-mode align` (only if absent) and this transfer configuration to its command:

```json
{"kv_connector":"LMCacheMPConnector","kv_connector_module_path":"lmcache.integration.vllm.lmcache_mp_connector","kv_role":"kv_both","kv_connector_extra_config":{"lmcache.mp.host":"tcp://lmcache-swift","lmcache.mp.port":5555,"lmcache.mp.autostart":false,"lmcache.mp.isolated_ipc":false,"lmcache.mp.lazy_offload":false}}
```

3. `baseline.override.yml` and `candidate.override.yml`: compose overrides for the existing `llama-swap` service. Each adds a read-only bind mount of its corresponding absolute YAML path at `/config/swift-ram-cache.yaml` and sets command to `["--config", "/config/swift-ram-cache.yaml", "--listen", "0.0.0.0:8080"]`. Preserve all other compose service configuration. Generate valid absolute paths; these artifacts must be generated on the future deployment host before use, not copied with workstation paths.

The script must not call Docker, SSH, Portainer, HTTP, or change the input. No new public model ID, capability downgrade, automatic activation, or silent cache bypass is introduced. The production `config.yaml` and `docker-compose.yml` remain untouched; repository polling cannot activate these files. The existing overcommitted co-residency matrix is not changed or exercised by this cache-only preparation.

### 4. Supply a bounded replay checker for later acceptance

Create `scripts/check_swift_ram_cache.py` using Python's standard-library HTTP/SSE support. There is no existing cache replay/throughput checker under `scripts/`; this script is the verification affordance for the uncertain hybrid cache path. It never starts/stops containers or changes model settings. Require explicit `--allow-inference` for any network request; missing authorization flag fails before connecting. Read an optional API token from `SWIFT_TEST_API_KEY`, never from a CLI argument or result log.

Implement these commands:

```text
python scripts/check_swift_ram_cache.py fixtures --output-dir DIRECTORY
python scripts/check_swift_ram_cache.py run --base-url URL --fixtures DIRECTORY --suite SUITE --output FILE --allow-inference
python scripts/check_swift_ram_cache.py compare --baseline FILE --candidate FILE
```

`fixtures` is offline. Generate deterministic, synthetic OpenAI chat payloads rather than saving private OMP transcripts. Reuse one fixed long system/tool prefix, two distinct session facts, and append turns without rewriting the prior prefix. Generate suites `decode`, `sessions`, `vision`, and `tools`:

- `decode`: three reproducible prompt-length classes (short ~2K, medium ~20K, long ~100K tokens), five requests each, sequential, maximum 1024 output tokens, temperature 0, identical non-thinking settings (`chat_template_kwargs.enable_thinking=false`) in baseline/candidate. Exact server-reported input/output token counts are recorded; approximate fixture labels must not be presented as exact counts. Warm one request per class before timing. Use `stream_options.include_usage=true`, record first content-token and final content-token timestamps, TTFT, and completion-token throughput excluding prefill. Aggregate reasoning/content consistently and do not count SSE packets as tokens. Missing usage/timing makes the sample invalid, not a zero or invented rate. Report the median per class; require at least 256 completion tokens in scored samples or mark that class inconclusive.
- `sessions`: two long sessions A/B, same prefix but different sentinel facts and tool schemas; alternate A/B for 20 turns, checking the requested session's sentinel and bounded valid structured answers. Include growing history and repeated-prefix suffix lengths around 1599, 1600, 1601, 3199, 3200, and 3201 token boundaries when a tokenizer is available; otherwise report those exact-boundary cases as not exercised, never infer token counts from characters. The fixture has fixed expected facts, so semantic correctness is machine-checkable without requiring identical prose. The same suite can be run before and after engine replacement.
- `vision`: generate distinct red/blue PNG data URLs locally using standard-library PNG construction. Use identical text with changed image bytes, repeat both requests, then perform a text follow-up. Check color answers and absence of stale cross-image reuse. Do not route around the cache connector or remove image capability to make it pass.
- `tools`: a named `lookup_record` tool with a required string `record_id`; request the session-specific sentinel via a forced named tool choice, validate parsed JSON arguments, append a matching tool result, and validate the follow-up. Also exercise the same cases with streaming deltas assembled into the final tool call.

Use the existing public model ID for every request. Requests use bounded output lengths and HTTP deadlines; HTTP errors, malformed streams, invalid tool arguments, timeouts, empty replies, and incorrect sentinel/color answers fail the suite. Save JSON results containing request identity, usage counts, durations, correctness, and any returned `kv_transfer_params.cached_token_stats`. Request that cache-stat field using `kv_transfer_params: {"cached_token_stats": {}}`; the pinned connector returns local/external hit counts when that key is present, but API propagation remains a runtime check. If absent, mark external hits unproven and use LMCache server counters/logs during later acceptance; an HTTP 200 alone never proves RAM reuse.

`compare` reads result files without network access. Reject unmatched fixtures/model/settings, failed correctness cases, missing decode classes, or unmeasured classes. Candidate median output throughput must be at least 95% of baseline in each class. Emit an explicit pass/fail/inconclusive verdict with the measured ratios; do not promote anything automatically.

Steps 1 and 2 can be implemented independently of the two scripts after the image tag/config contract above is fixed. Integration and local verification happen after all four artifacts exist.

## Verification

### Allowed now: preparation proof only

Run from repository root. Do not SSH to run builds, start containers with GPU access, send inference, reset caches, trigger Portainer, push Git changes, or restart any live service.

1. Exercise the renderer using `uv run scripts/prepare_swift_ram_cache.py --source services/llama-swap-vllm/config.yaml --output-dir /tmp/swift-ram-cache-check-UNIQUE`. Supply a newly created unique temporary path rather than literally reusing `UNIQUE`. Confirm baseline/candidate parse, retain the same public model/capabilities/MTP, and differ only as specified. Exercise absent Swift entry, conflicting existing connector, an existing output file, and a source/output collision; each must fail without altering input or earlier outputs. These are observable safety behaviors, not tests of YAML wording.
2. With dummy `LLAMA_SWAP_API_KEY` and `HF_TOKEN` values, `docker compose -f services/llama-swap-vllm/docker-compose.yml -f services/llama-swap-vllm/compose.lmcache.yml config --quiet` must succeed without starting services. Validate each generated router override merged after these two files, also solely through `config --quiet`; never print rendered credentials.
3. Build on a local Linux/amd64-capable Docker builder, not the inference host:
   `docker buildx build --platform linux/amd64 -f images/vllm-fastokens/Dockerfile.lmcache -t swift-ram-cache:vllm-0.29.0-lmcache-0.5.5 --load images/vllm-fastokens`.
   Run GPU-free imports, `pip check`, and `lmcache server --help` in the candidate. Verify unchanged protected-package versions and presence of the external connector. If a suitable local builder is unavailable, finish the source artifacts and local script/compose checks, explicitly report the image build as unverified; do not move it to the live host.
4. Run `fixtures`, exercise `compare` with local result fixtures representing 4% and 6% regressions (pass and fail), and check incomplete measurements produce inconclusive. Verify `run` without `--allow-inference` exits before network access. A throwaway local SSE server may validate usage/timing and tool-delta parsing; do not target the inference host. Keep regression tests only for safety/stream parsing boundaries that can plausibly break.
5. Deliver the prepared files and exact build/render/check commands. Explicitly state: no live deployment, external-hit proof, vision-cache validation, throughput claim, or co-residency claim has been established.

### Deferred runtime acceptance: requires a separately authorized maintenance window

Provide these steps as the execution protocol, not commands to run during preparation:

1. On `inference-box`, obtain a baseline router config matching the currently intended engine settings, render both variants there, and save the baseline image identity/flags. Ensure no other GPU workload is active. Wait for existing requests to drain; stop if they do not drain. Record host `MemAvailable`, swap use, free GPU memory, and baseline startup cache capacity. Run the baseline suites with `--base-url` pointing to the existing public endpoint and API key provided through the environment.
2. Build/load the candidate image ahead of the maintenance window. Start only the sidecar in the existing stack with `docker compose -f services/llama-swap-vllm/docker-compose.yml -f services/llama-swap-vllm/compose.lmcache.yml up -d --no-deps lmcache-swift`. Observe health, then activate the candidate by adding the generated candidate override as the third compose file and targeting only `llama-swap` for the deliberate redeploy. Keep the sidecar running throughout model unload/reload checks. Never launch baseline and candidate simultaneously at 0.9 allocation. Use original Portainer environment values securely; do not create an env_file.
3. Confirm external connector selection, MTP=3, FP8 KV, hybrid manager enabled, and actual unified block size 1600. If the candidate resolves a different size, stop that trial and regenerate the cache service chunk argument to the reported size before testing; keep the model's native block geometry rather than forcing 1600 on the engine. A changed checkpoint/runtime requires new fixtures and an empty LMCache service before any reuse.
4. Run candidate cold, GPU-warm, and external-warm cases separately. For external-warm: populate sessions A/B, observe completed stores, drain requests and gracefully unload only Swift (never LMCache), reload the identical candidate, and replay the sessions. Confirm positive external retrieved-token/byte counts with correct answers. This proves reuse across removal, rather than merely GPU prefix hits. Allow incomplete tails to recompute. Repeat unload/reload twice. Record engine startup time separately from post-readiness TTFT.
5. Run all suites, compare identical settings, and require the 5% per-class decode threshold. Require external-warm median TTFT to beat cold prefill on medium/long prefixes with positive external hits; report the measured improvement rather than setting an unsupported promised percentage. Confirm interleaved-session, tool, image-change, and streamed-output correctness. Run an additional 40-minute alternating-session soak with confirmed external retrieval and bounded outputs; silent corruption, looping, or cross-session/image leakage fails immediately. GDN output need not be byte-identical, but expected facts/tool arguments must be correct.
6. Observe the 16 GiB cache cap, service memory under 20 GiB, `MemAvailable >= 8 GiB`, no sustained swap growth, no OOMs, stable MTP acceptance, and full 262144 Swift context capacity. Full-length request feasibility is a separate bounded long-prompt smoke case (prompt plus output within 262144); a startup log alone does not establish long-request runtime stability.
7. On any correctness, memory, ABI, or performance gate failure, drain and unload the candidate, restore the generated baseline override and original image, and stop only `lmcache-swift` after baseline recovery. Do not use whole-stack `down` for rollback. Preserve diagnostics. Do not disable MTP/vision, change quantization, add patches, or reduce the GPU budget to force a pass. Promotion to a permanent GitOps configuration is a separate change after evidence exists; these preparation artifacts do not silently activate it.

## Critical files & anchors

- `services/llama-swap-vllm/config.yaml`: `DOCKER_PREFIX`, `VLLM_COMMON`, Swift entry (around 252–305), and `routing` (around 621). Source of truth for rendering; do not copy a second model catalogue into Git.
- `services/llama-swap-vllm/docker-compose.yml`: git-sync and router command/mounts. Distinguishes safe staged files from active configuration.
- `images/vllm-fastokens/Dockerfile`: production vLLM pin, fastokens install, and Froggeric template. Leave unchanged.
- `.github/workflows/build-images.yml`: `images/*/Dockerfile` discovery and publish-on-main behavior. Leave unchanged so the candidate cannot replace production latest.
- `scripts/`: existing Python maintenance-script location; no equivalent cache preparation/replay utility was found.

## Assumptions & contingencies

- User-selected priorities: unload-surviving RAM cache first, unchanged Swift GPU budget and endpoint, maximum 5% steady-state decode regression, no live testing in this execution. Do not add Nemotron residency or reboot persistence.
- Cache retention is best-effort within the 16 GiB LRU tier. Evicted entries, unfinished stores, changed prefixes, or cache-service restarts may require recomputation; OMP remains responsible for complete conversation history.
- If the exact runtime cannot build/import the pinned connector under preserved core dependencies, deliver the failed compatibility evidence and inactive preparation artifacts. Do not claim a deployable runtime or automatically choose a newer vLLM/LMCache release.
- If live validation later fails, baseline recovery is mandatory and further optimization requires a new decision. A prepare-only result is complete for the selected scope, but it is not production acceptance.
