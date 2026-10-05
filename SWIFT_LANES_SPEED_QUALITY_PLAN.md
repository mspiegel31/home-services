# Swift lanes: speed tuning, NVFP4 quality, suffix decoding, and a Harbor eval baseline

## Context

The inference box (`inference-box`, 192.168.1.98, ssh user `cloud`; Proxmox VM 600 `ai-llm`; RTX PRO 5000 72 GB on PCIe 4.0 x16) serves Swift 1.5 lanes through llama-swap (`services/llama-swap-vllm`). This work has five parts:

1. Speed up the d0xin Swift Flash NVFP4 MoE lane.
2. Apply the useful Proxmox and guest settings.
3. Get dense Swift decode faster, using FP8 + MTP and suffix decoding on BF16.
4. Test whether NVFP4 gets "smarter" with BF16 activations.
5. Stand up a reproducible Harbor + Terminal-Bench eval baseline, so quality claims rest on measurements.

End state:
- Speed tunings that meet the measured rules below are committed.
- Eval and bench tooling lives in the repo.
- `services/llama-swap-vllm/SWIFT_LANES.md` records every number.
- Quality trade-offs are reported for the user to decide, not adopted automatically.

## Measured facts this plan relies on (2026-10-04)

- **d0xin lane is limited by PCIe bandwidth.**
  - 17.09 GiB of routed experts are offloaded to host RAM through UVA (`--cpu-offload-gb 17 --cpu-offload-params experts`).
  - During decode, rx is 22–30 GB/s, the practical ceiling of Gen4 x16, with SM at 100%.
  - Decode is about 30 tok/s single-stream and about 15 tok/s per stream with 2–3 streams.
  - MTP3 acceptance by draft position is 0.70 / 0.50 / 0.36.
  - The LIL image accepts `--language-model-only` and `--cpu-offload-params`. Segment matching is used: `embed_tokens` matches `model.language_model.embed_tokens.weight`.
- **Dense lanes are limited by GPU memory bandwidth.**
  - Weight sizes: BF16 decoder 48.71 GB, Quark FP8 decoder 24.39 GB, `lm_head` 2.54 GB in BF16 in both, MTP head about 0.85 GB.
  - Estimated decode with MTP3: BF16 about 34 tok/s, FP8 about 56 tok/s.
- **`swift-1.5-fp8` has no spec decode.**
  - Quark `quantization_config.exclude` lists `mtp.*` plus `mtp.*.weight` names.
  - vLLM 0.30's `should_ignore_layer` → `find_matching_patterns` only matches exact module names or `re:` regexes, so MTP layers are built in FP8 and reject the BF16 tensors.
  - The checkpoint has 15 BF16 `mtp.*` tensors.
  - The HF hub snapshot that vLLM loads is `/mnt/models/huggingface/hub/models--ukisai--Swift-1.5-Qwen3.8-27b-Quark-FP8-dynamic-AMD/snapshots/e69fcf47f01060a3cde61fb1f79bbfb5a4bb1ebb/`. Its `config.json` is a symlink into `blobs/`.
  - Precedent: the AWQ snapshot already carries a patched regular-file `config.json` plus `config.json.orig`.
- **`swift-1.5-nvfp4` (`ukisai/Swift-1.5-Qwen3.8-27b-NVFP4`) is W4A4.**
  - MLP and `lm_head` are NVFP4 with static FP4 activation scales. Attention and GDN are FP8 W8A8.
  - vLLM's `_get_linear_backend(quantization="nvfp4_w4a4")` honors `kernel_config.linear_backend_per_quant`. It logs `Applied linear backend override for 'nvfp4_w4a4': 'marlin'`.
  - Marlin runs the same weights with BF16 activations.
  - This exact override booted on this lane before (commit 3cfc75f; removed in 0518a0f).
- **Suffix decoding:**
  - vLLM 0.30's `method: "suffix"` lazily imports `arctic_inference.suffix_decoding.SuffixDecodingCache`.
  - It calls `start_request`, `add_active_response`, `speculate(req_id, pattern, max_spec_tokens=, max_spec_factor=, min_token_prob=)`, `stop_request`, `evict_cached_response`, `active_requests`, and `cached_requests`.
  - `arctic-inference==0.3.0` (released 2026-08-28; repo last pushed 2026-09-23) matches those signatures.
  - It ships as an sdist only. Its only default compiled extension is the CPU C++ `arctic_inference.suffix_decoding._C`, built with nanobind; the CUDA ops are built only if `ARCTIC_INFERENCE_PRECOMPILED_OPS=1`.
  - Its vLLM patch plugin (entry point `vllm.general_plugins`) returns immediately unless `ARCTIC_INFERENCE_ENABLED=1`. That makes its pin to vLLM 0.26 irrelevant here.
  - The `vllm-fastokens` base has torch 2.13+cu130, g++, ninja, Python 3.12 headers, numpy 2.2.6, protobuf 6.33.6, and grpcio 1.84.0. It has no cmake, nanobind, or grpcio-tools.
- **Harbor:**
  - `harbor==0.23.0` with the `terminus-2` agent. The agent loop runs on the host, so `api_base` can be loopback.
  - The `hosted_vllm/<model>` LiteLLM provider reads `HOSTED_VLLM_API_KEY`.
  - CLI flags resolve correctly with `-p <dataset> -i <task>… -m hosted_vllm/<id> --ak api_base=… --ak 'llm_call_kwargs={…}' --ak 'model_info={…}' -k N -n N` (checked with `--print-config`).
  - `-m` does NOT override `agents[].model_name` from a `-c` config file, so the runner uses CLI flags only.
  - Per-trial results are `<job_dir>/<trial>/result.json` (`TrialResult`: `task_name`, `verifier_result.rewards`, `exception_info.exception_type`, `started_at`, `finished_at`).
  - Terminal-Bench 2.0 is pinned at `https://github.com/harbor-framework/terminal-bench-2` commit `2fd12b88aafdd04a52c298e3940bcb189f9766d6`. The 12 tasks used here have amd64 images of 0.03–0.3 GB and a 900 s agent timeout. Verifiers write `reward.txt` (1 or 0).
- **Router mechanics:**
  - llama-swap reads config only at startup.
  - git-sync pulls `main` every 30 s into volume `llama-swap_llama-swap-config`, mounted at `/config/current/...` in container `llama-swap-vllm`.
  - Backends are `docker run --rm` containers named `vllm-<model id with . → ->`, labeled `io.mspiegel.llama-swap.managed=true`.
  - Router is at `127.0.0.1:11437` on the box. It needs `Authorization: Bearer $LLAMA_SWAP_API_KEY`, which is present in `docker inspect llama-swap-vllm` env.
  - vLLM `/metrics` on `http://vllm-<…>:8000/metrics` exposes `vllm:spec_decode_num_accepted_tokens_total{…}` and `vllm:spec_decode_num_drafts_total{…}`.
  - Docker root is `/mnt/models/docker` (103 GB free).

## Approach

Phases 1–3 are independent of each other. Phases 4–8 run in order on the box. Temporary lane variants follow the repo precedent (commits 68bbf47 / adb1ab6): a commit titled `<lane>: TEMPORARY <change> for <experiment>`, pushed to `main`, activated, measured, then reverted or superseded by a final commit that documents the measurement in the lane's comment block.

### Phase 1 — VM and guest settings (user performs the Proxmox part)

1. **User, in the Proxmox UI:**
   - VM 600 → Hardware → PCI Device (hostpci0) → Advanced → tick **PCI-Express** → OK. Equivalent CLI: `qm set 600 --hostpci0 0000:2b:00,pcie=1`.
   - Then **Shutdown** and **Start** the VM from Proxmox. A reboot from inside the guest does not apply pending hardware changes.
   - Make no other VM changes: no hugepages (THP already backs all 112 GiB: `AnonHugePages: 117391360 kB`), no CPU pinning (steal is 0).
2. **Guest, as `cloud`:** run `echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/90-swappiness.conf && sudo sysctl --system`. If sudo needs a password, the user runs it.

### Phase 2 — Generalize the decode bench and the prefix-cache canary

3. **Rewrite `services/llama-swap-vllm/bench_spec_decode.py` to be lane-agnostic.**
   - Signature: `python3 /bench.py <label> <model-id> [--workload prose|edit|both]`, parsed with `argparse`; default `both`.
   - Derive `base = f"http://vllm-{model_id.replace('.', '-')}:8000"`. Use `base + "/v1/chat/completions"` and `base + "/metrics"`.
   - `stream(prompt, max_tokens, temperature=0.7)` gains a `model` argument. Delete the `BASE` constant and the hardcoded `"qwen3.8-27b-fp8"`.
   - Add `spec_counters(base) -> tuple[float, float] | None`.
     - It fetches `/metrics` and sums values on lines starting with `vllm:spec_decode_num_accepted_tokens_total{` and `vllm:spec_decode_num_drafts_total{`.
     - It returns `None` when neither metric is present (no spec decode).
   - Each workload records counters before and after its runs. It reports `mean_acceptance_length = 1 + Δaccepted/Δdrafts`, or `null` when counters are `None` or `Δdrafts == 0`.
   - **`prose` workload:** the existing flow, unchanged. That means the prefix warm-up, 3 cached runs, and 1 cold run, with `INSTRUCTION`, 320 tokens, and thinking off.
   - **`edit` workload (new):**
     - Prompt: `"Return the complete file below unchanged except rename the function `stream` to `stream_chat` everywhere it appears. Output only the code, no commentary.\n```python\n" + open(__file__).read() + "\n```"`.
     - `max_tokens=3072`, 3 runs, thinking off.
     - This is a copy-heavy proxy for agent edit turns, using the script's own source so it is deterministic.
   - Output is one JSON object: `{"label", "model", "prose": {...existing cached/cold fields..., "mean_acceptance_length"}, "edit": {"decode_tps": [...], "median_decode_tps", "completion_tokens": [...], "mean_acceptance_length"}}`. Omit the key of a workload that wasn't run.
   - Update the module docstring's command to `docker run --rm --entrypoint python3 --network llama-swap-vllm-backend -v "$PWD/bench_spec_decode.py:/bench.py:ro" ghcr.io/mspiegel31/vllm-fastokens:latest /bench.py <label> <model-id>`. The explicit `--entrypoint python3` avoids the image's `vllm` entrypoint.
4. **Generalize `services/llama-swap-vllm/canary_prefix_cache.py` the same way.**
   - First run `grep -n 'qwen3' services/llama-swap-vllm/canary_prefix_cache.py`. The known hits are the `BASE` constant (~line 45) and the request `"model"` (~line 51).
   - Replace every hit with values derived from `sys.argv[1]`, the model id, using the same `vllm-` container rule. Exit with usage text if `argv[1]` is missing.
5. **Update the two `docker run` commands under "Reproducing" in `services/llama-swap-vllm/BENCHMARKS.md`** to the new argument form (`<label> <model-id>` and `<model-id>`) with `--entrypoint python3`. These are the only other callsites; `grep -rn 'bench.py\|canary.py' services` must return just those lines plus the two docstrings.

### Phase 3 — Eval tooling: Harbor runner, lane helpers, and the suffix-capable image

6. **Create `services/llama-swap-vllm/evals/`** with these files. All shell scripts start with `#!/usr/bin/env bash` and `set -euo pipefail`. They run on the box from a repo clone, which Phase 4 creates.
   - **`lane_env.sh`** (sourced by the others):
     - `export LLAMA_SWAP_KEY=$(docker inspect llama-swap-vllm --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^LLAMA_SWAP_API_KEY=//p')`. If the result is empty, exit 1 with `LLAMA_SWAP_API_KEY not found in llama-swap-vllm env`.
     - Define `container_for() { echo "vllm-${1//./-}"; }`.
   - **`activate_config.sh <models-file-basename> <needle>`**:
     1. Poll every 5 s, up to 180 s, until `docker exec llama-swap-vllm grep -qF -- "<needle>" /config/current/services/llama-swap-vllm/models/<basename>` succeeds. On timeout, exit 1 with `git-sync has not delivered <needle>`.
     2. Run `docker restart -t 120 llama-swap-vllm`.
     3. Stop every container from `docker ps --filter label=io.mspiegel.llama-swap.managed=true --format '{{.Names}}'` with `docker stop --time 90`.
     4. Wait until `curl -fsS -H "Authorization: Bearer $LLAMA_SWAP_KEY" http://127.0.0.1:11437/v1/models` succeeds, up to 120 s.
   - **`warm_lane.sh <model-id>`**:
     - Run `curl -fsS --max-time 3600 -H "Authorization: Bearer $LLAMA_SWAP_KEY" -H 'Content-Type: application/json' http://127.0.0.1:11437/v1/chat/completions -d '{"model":"<id>","messages":[{"role":"user","content":"Reply with: ready"}],"max_tokens":8,"chat_template_kwargs":{"enable_thinking":false}}'`.
     - Print `docker logs --tail 200 $(container_for <id>) 2>&1 | grep -E 'GPU KV cache size|Applied linear backend override|speculative|Avg Draft'`.
   - **`quiesce.sh pause|unpause`**: runs `docker pause litellm bifrost` or `docker unpause litellm bifrost`. This stops production clients from triggering lane swaps during measurements.
   - **`bench_lane.sh <model-id> <label>`**: `warm_lane.sh`, then the bench `docker run` from step 3 with `/bench.py <label> <model-id>`. It tees output to `/mnt/models/evals/bench/<model-id>__<label>__$(date +%Y%m%d-%H%M).json`.
   - **`run_harbor.sh <model-id> <variant-label>`**, with these defaults:
     - `TB2=${TB2:-/mnt/models/evals/terminal-bench-2}`, `JOBS=${JOBS:-/mnt/models/evals/jobs}`.
     - `TASKS=${TASKS:-"fix-git git-leak-recovery sanitize-git-repo git-multibranch log-summary-date-ranges regex-log sqlite-db-truncate db-wal-recovery build-cython-ext nginx-request-logging multi-source-data-merger openssl-selfsigned-cert"}`.
     - `ATTEMPTS=${ATTEMPTS:-3}`, `CONCURRENCY=${CONCURRENCY:-4}`.

     It then:
     1. Exports `HOSTED_VLLM_API_KEY=$LLAMA_SWAP_KEY` and runs `warm_lane.sh`.
     2. Records `docker inspect -f '{{.State.StartedAt}}' $(container_for <id>)`.
     3. Runs:
        ```
        harbor run -p "$TB2" <-i task for each in $TASKS> -a terminus-2 -m "hosted_vllm/<id>" \
          --ak api_base=http://127.0.0.1:11437/v1 \
          --ak 'llm_call_kwargs={"extra_body":{"chat_template_kwargs":{"enable_thinking":true,"reasoning_effort":"xhigh"}}}' \
          --ak 'model_info={"max_input_tokens":131072,"max_output_tokens":32768,"input_cost_per_token":0,"output_cost_per_token":0}' \
          ${PARSER:+--ak parser_name=$PARSER} \
          -k "$ATTEMPTS" -n "$CONCURRENCY" --agent-timeout-multiplier 4 -y \
          -o "$JOBS" --job-name "<id>__<variant>__$(date +%Y%m%d-%H%M)"
        ```
     4. Re-reads `StartedAt`. If it changed, it prints `WARNING: lane container restarted during the job; discard and rerun` and exits 2.

     Notes on these values:
     - Temperature is left unset, so each lane uses its checkpoint generation defaults.
     - Do not set terminus-2's own `reasoning_effort`, because that would send a top-level field that vLLM auto-translates.
     - The 4× agent timeout keeps slow lanes from failing on speed alone. Wall time is reported separately.
   - **`summarize_harbor.py <job_dir>...`** (stdlib only; no equivalent exists in the repo):
     - For each job dir, glob `*/result.json` and parse it as `TrialResult`.
     - **Reward:** if `verifier_result.rewards` has exactly one key, use its value. If it is `None` or the trial has `exception_info`, the reward is 0. If there is more than one key, exit 1 and list the keys.
     - **Pass:** reward ≥ 1.
     - **Per-job markdown row:** job name, trials, passes, errored count by `exception_info.exception_type`, pass rate, Wilson 95% interval, median trial minutes (`finished_at - started_at`).
     - **Task matrix:** one row per task, one column per job, cells `passes/attempts`.
     - **Paired comparison:** when the first job given is the reference, print per-task pass differences against it.
7. **Add suffix decoding support to the shared image `images/vllm-fastokens/Dockerfile`** as a multi-stage build:
   ```
   FROM vllm/vllm-openai:v0.30.0@sha256:8a69ffad015f138d7170c4ddc429e230a3bc1c1719f67e14324749df200a4b90 AS arctic-build
   RUN pip install --no-cache-dir 'cmake>=3.18' 'nanobind==2.9.2' grpcio-tools wheel ninja \
    && pip wheel --no-build-isolation --no-deps --no-cache-dir 'arctic-inference==0.3.0' -w /wheels

   FROM vllm/vllm-openai:v0.30.0@sha256:8a69ffad015f138d7170c4ddc429e230a3bc1c1719f67e14324749df200a4b90
   RUN pip install --no-cache-dir 'fastokens>=0.2.0,<0.3'
   COPY --from=arctic-build /wheels /tmp/wheels
   RUN pip install --no-cache-dir --no-deps /tmp/wheels/arctic_inference-*.whl && rm -rf /tmp/wheels
   ```
   Keep the existing froggeric `COPY` and its comment.

   Add a comment explaining:
   - vLLM's built-in `method: "suffix"` only needs the CPU suffix tree.
   - The build tools stay in the builder stage, so they can't change the runtime protobuf/grpcio.
   - `--no-deps` keeps the arctic vLLM extras from installing.
   - The arctic plugin stays inert unless `ARCTIC_INFERENCE_ENABLED=1`; never set it.

   Pushing to `main` triggers `.github/workflows/build-images.yml`, which builds `linux/amd64,linux/arm64` and publishes `latest` plus the short sha.

### Phase 4 — Box setup and harness smoke test

8. **On the box, as `cloud`:**
   1. `curl -LsSf https://astral.sh/uv/install.sh | sh`
   2. `~/.local/bin/uv tool install harbor==0.23.0`
   3. `git clone https://github.com/mspiegel31/home-services.git ~/home-services` (or `git -C ~/home-services pull` if it already exists)
   4. `mkdir -p /mnt/models/evals/{jobs,bench}`
   5. `git clone https://github.com/harbor-framework/terminal-bench-2 /mnt/models/evals/terminal-bench-2 && git -C /mnt/models/evals/terminal-bench-2 checkout 2fd12b88aafdd04a52c298e3940bcb189f9766d6`
9. **After CI publishes the image,** run `docker pull ghcr.io/mspiegel31/vllm-fastokens:latest`.
10. **Harness smoke test** against the currently loaded d0xin lane: `evals/quiesce.sh pause`, then `TASKS=fix-git ATTEMPTS=1 CONCURRENCY=1 evals/run_harbor.sh swift-1.5-flash-nvfp4-d0xin smoke`, then `evals/summarize_harbor.py /mnt/models/evals/jobs/swift-1.5-flash-nvfp4-d0xin__smoke__*`. Expected: one trial with reward 0 or 1, no `exception_info`, and the summarizer prints a row. Keep litellm and bifrost paused through Phase 8, unpausing only between work sessions.

### Phase 5 — d0xin MoE lane speed tuning (`models/swift-1.5-flash-nvfp4-d0xin.yaml`)

11. **Spec-token sweep.**
    - Baseline: `evals/bench_lane.sh swift-1.5-flash-nvfp4-d0xin mtp3`.
    - Then for N in 2, then 1:
      1. Commit `swift-1.5-flash-nvfp4-d0xin: TEMPORARY MTP<N> for spec-token sweep`, changing only `"num_speculative_tokens":3` to `<N>`.
      2. Push, then `evals/activate_config.sh swift-1.5-flash-nvfp4-d0xin.yaml '"num_speculative_tokens":<N>'`.
      3. `evals/bench_lane.sh swift-1.5-flash-nvfp4-d0xin mtp<N>`.
    - **Winner:** highest mean of `prose.cached.median_decode_tps` and `edit.median_decode_tps`. If within 5% of a smaller N, take the smaller N.
    - Commit the winner as a normal commit, `Set d0xin MTP<N> after spec-token sweep`. Its comment block records all three measurements and acceptance lengths, replacing the "Acceptance rates are unmeasured" sentence.
12. **Lean-memory variant**, a temporary commit on top of the winner. Replace these flags:
    - `--max-model-len 262144` → `--max-model-len 131072`
    - add `--language-model-only`
    - `--cpu-offload-gb 17 --cpu-offload-params experts` → `--cpu-offload-gb 12 --cpu-offload-params embed_tokens experts`

    Then activate (needle `--language-model-only`) and warm.
    - **Sizing loop:** read `GPU KV cache size: <T> tokens` from the warm output.
      - If startup OOMs or `T < 137626` (131072 × 1.05), raise `--cpu-offload-gb` by 1 in a new temporary commit and repeat, up to 17.
      - If startup fails with an error naming `embed_tokens`, drop `embed_tokens` from `--cpu-offload-params` and add 1 to `--cpu-offload-gb`.
    - Bench it as `lean`.
    - **Adopt** if `prose.cached.median_decode_tps` is ≥ 1.10× the winner's. In the same final commit, set:
      - `capabilities.in: ["text"]`
      - `capabilities.context: 131072`
      - `metadata.vision: false`
      - `description` updated to the new KV, context, and draft settings
      - in `services/litellm/models/swift-1.5-flash-nvfp4-d0xin.yaml`: `vision: false`, `supports_vision: false`, and `context_window`, `max_input_tokens`, `max_output_tokens` all `131072`
    - Rewrite the lane comment block's KV and offload paragraph with the measured `T` and the final offload GiB.
    - Keep the "Do NOT set max-num-batched-tokens above 4096" note.
    - **Otherwise**, revert the temporary commits so the lane returns to the sweep winner.

### Phase 6 — FP8 dense lane: enable MTP

13. **Patch the Quark exclude list** in the HF snapshot without sudo. Use the image as root:
    ```
    docker run --rm --entrypoint python3 -v /mnt/models:/models ghcr.io/mspiegel31/vllm-fastokens:latest -c '
    import json, os, shutil
    d = "/models/huggingface/hub/models--ukisai--Swift-1.5-Qwen3.8-27b-Quark-FP8-dynamic-AMD/snapshots/e69fcf47f01060a3cde61fb1f79bbfb5a4bb1ebb"
    p = d + "/config.json"
    if not os.path.exists(p + ".orig"):
        shutil.copyfile(p, p + ".orig", follow_symlinks=True)
    c = json.load(open(p + ".orig"))
    ex = c["quantization_config"]["exclude"]
    if "re:^mtp\\..*" not in ex:
        ex.append("re:^mtp\\..*")
    os.unlink(p)
    json.dump(c, open(p, "w"), indent=2)
    print(len(ex))'
    ```
    It should print `226`. The `blobs/` file is left untouched, mirroring the AWQ precedent.
14. **Edit `models/swift-1.5-fp8.yaml`:**
    - Append `--speculative-config '{"method":"mtp","num_speculative_tokens":3}'` before `${QWEN38_COMMON}`.
    - Replace the "No speculative decoding: …untested." comment paragraph with a paragraph in the AWQ lane's wording. It must cover: the `re:^mtp\..*` exclude added to the cached snapshot `config.json`; the backup at `config.json.orig`; that a re-download restores the broken config and the lane loses MTP; and to check `Avg Draft acceptance rate`.
    - Replace "Runtime not yet validated…" with the measured KV line from the warm output.
    - Change `description` to `… with bf16 KV, native MTP3 spec decode, and 262,144 context`.

    Then commit, push, activate (needle `"method":"mtp"`), and warm.
15. **Measure:**
    - `evals/bench_lane.sh swift-1.5-fp8 mtp3`.
    - `docker run --rm --entrypoint python3 --network llama-swap-vllm-backend -v "$PWD/services/llama-swap-vllm/canary_prefix_cache.py:/canary.py:ro" ghcr.io/mspiegel31/vllm-fastokens:latest /canary.py swift-1.5-fp8`. The canary must report `margin_equal`, `no_leak`, and `no_degeneration` all true.
    - If the canary fails, append `--no-enable-prefix-caching` to the lane `cmd` and add a comment citing the canary result.

### Phase 7 — BF16 dense lane: suffix decoding A/B (requires Phase 3 step 7 image)

16. **Check that the image is inert for existing lanes.**
    - `evals/bench_lane.sh swift-1.5-bf16 mtp3` on the new image.
    - The lane must become healthy. `docker logs vllm-swift-1-5-bf16 2>&1 | grep -i 'arctic inference is enabled'` must print nothing.
17. **Suffix variant.**
    - Commit `swift-1.5-bf16: TEMPORARY suffix decoding for spec A/B`, replacing the `--speculative-config` value with `'{"method":"suffix"}'`. vLLM defaults then apply: max tree depth 24, and `num_speculative_tokens` defaults to 24.
    - Push, activate (needle `"method":"suffix"`), and bench as `suffix`. Run the canary with `/canary.py swift-1.5-bf16`.
    - **Adopt** suffix (normal commit with measurements in the lane comment, and `description` changed from "native MTP3" to "suffix decoding") only if all three hold:
      - `edit.median_decode_tps` ≥ 1.20× MTP3's
      - `prose.cached.median_decode_tps` ≥ 0.90× MTP3's
      - the canary passes
    - **Otherwise**, revert the temporary commit.

### Phase 8 — Harbor quality matrix and results record

18. **Run `evals/run_harbor.sh <id> <variant>`** with the defaults (12 tasks × 3 attempts, xhigh thinking), in this order to minimize lane swaps:
    1. `swift-1.5-bf16 final` (reference)
    2. `swift-1.5-fp8 final`
    3. `swift-1.5-awq final`
    4. `swift-1.5-nvfp4 w4a4`
    5. `swift-1.5-nvfp4 w4a16`: a temporary commit `swift-1.5-nvfp4: TEMPORARY Marlin W4A16 for activation-precision eval` adding `--kernel-config '{"linear_backend_per_quant":{"nvfp4_w4a4":"marlin"}}'` right after `${VLLM_COMMON}`. Activate with needle `nvfp4_w4a4`. Warm output must show `Applied linear backend override for 'nvfp4_w4a4': 'marlin'`. Also run `evals/bench_lane.sh swift-1.5-nvfp4 w4a16` and `… w4a4` (before the temporary commit) for the speed column. Revert the temporary commit afterward.
    6. `swift-1.5-flash-nvfp4-d0xin final`

    Rerun any job where `run_harbor.sh` exits 2. Skip a lane that fails to boot, and record the boot error in its row.
19. **Create `services/llama-swap-vllm/SWIFT_LANES.md`** in the structure of `BENCHMARKS.md`:
    - **Environment:** image digest, harbor 0.23.0, TB2 commit, task list, attempts, timeouts, xhigh.
    - **Decode table:** per lane and variant, prose and edit median tok/s and mean acceptance length, from `/mnt/models/evals/bench/*.json`.
    - **Results by phase:** the d0xin sweep and lean result, the FP8 MTP result, and the suffix A/B result, each with the adopt/revert decision and rule.
    - **Harbor:** the `summarize_harbor.py` output with `swift-1.5-bf16__final` as the first (reference) job.
    - **Method caveats:**
      - litellm and bifrost were paused during runs.
      - 36 trials per lane only resolve gaps of roughly 20 points or more.
      - The W4A16 kernel changes only NVFP4 layers; the FP8 W8A8 attention/GDN layers keep FP8 activations.

## Critical files & anchors

- `services/llama-swap-vllm/models/swift-1.5-flash-nvfp4-d0xin.yaml`: `cmd` lines with `--max-model-len`, `--cpu-offload-*`, and `--speculative-config` (≈87–98), plus the KV comment paragraph (≈52–65), which must be rewritten with the measured values.
- `services/llama-swap-vllm/models/swift-1.5-fp8.yaml`: the comment paragraph at ≈35–39 and the `cmd` tail. This is the only lane gaining a new spec config.
- `services/llama-swap-vllm/bench_spec_decode.py`: `BASE` (line 27), `stream()` (31–73), `main()` (76–103). This is where the lane-agnostic arguments and the metrics delta go.
- `images/vllm-fastokens/Dockerfile`: the shared image for most lanes. The builder-stage isolation is what keeps the runtime protobuf/grpcio unchanged.
- `services/llama-swap-vllm/models/swift-1.5-nvfp4.yaml`: the insertion point for the temporary `--kernel-config`, right after `${VLLM_COMMON}`.

## Verification

- **Phase 1:**
  - `lspci -tv` shows the NVIDIA GPU under a `00:1c.x` root port, not `00:1e.0`.
  - `nvidia-smi --query-gpu=pcie.link.gen.current,pcie.link.width.current --format=csv` → `4, 16`.
  - `cat /proc/sys/vm/swappiness` → `10`.
- **Phase 2:**
  - `evals/bench_lane.sh swift-1.5-flash-nvfp4-d0xin mtp3` prints JSON with both `prose` and `edit` keys.
  - Both workloads have a non-null `mean_acceptance_length` between 1 and 4.
  - `edit.completion_tokens` is above 1000, which shows the file was copied back.
  - The same command against `swift-1.5-fp8` before Phase 6 prints `mean_acceptance_length: null`.
- **Phase 3 image:** on the box after the pull, run
  ```
  docker run --rm --entrypoint python3 ghcr.io/mspiegel31/vllm-fastokens:latest -c "from arctic_inference.suffix_decoding import SuffixDecodingCache as C; c=C(max_tree_depth=24,max_cached_requests=10); c.start_request('r',[1,2,3,4,1,2,3]); c.add_active_response('r',[4]); print(c.speculate('r',[1,2,3,4,1,2,3,4]).token_ids)"
  ```
  It must print a Python list with no exception. Also run `docker run --rm --entrypoint python3 ghcr.io/mspiegel31/vllm-fastokens:latest -c "import google.protobuf, grpc; print(google.protobuf.__version__, grpc.__version__)"`, which must print `6.33.6 1.84.0`.
- **Phase 4:** the smoke test from step 10 yields one parsed trial with no exception.
- **Phases 5–7:** each adopted change has a bench JSON in `/mnt/models/evals/bench/` that meets its stated rule. The FP8 and suffix canaries print all three checks true. `git log --oneline` shows every TEMPORARY commit followed by its revert or final commit.
- **Phase 8:** `evals/summarize_harbor.py /mnt/models/evals/jobs/*__final__* /mnt/models/evals/jobs/swift-1.5-nvfp4__w4a4__* /mnt/models/evals/jobs/swift-1.5-nvfp4__w4a16__*` prints six rows, each with 36 trials, and a 12-row task matrix.
- **Final state:** `git status` is clean, the router is restarted on final `main`, and `evals/quiesce.sh unpause` has run.

## Assumptions & contingencies

- **Production downtime.** litellm and bifrost are paused from the Phase 4 smoke test through Phase 8 (production clients are down during eval sessions). If the user needs them back mid-way, unpause between lanes, never during a job.
- **Quality trade-offs are reported, not adopted.** The W4A16 Marlin variant is reverted after its eval regardless of score. The user decides from `SWIFT_LANES.md` whether to make it permanent.
- **The lean d0xin variant gives up vision and long context.** If adopted under the ≥10% rule, the lane drops image input and goes from 262,144 to 131,072 context. The user can veto by reverting that commit.
- **Harbor results.** If the reward key differs from expectations but is a single key, the summarizer already handles it. If the smoke trial raises an exception from response parsing, rerun the smoke with `PARSER=xml` and use `PARSER=xml` for every lane.
- **Eval directory.** If `/mnt/models/evals` is not writable by `cloud`, use `~/evals` for `TB2`, `JOBS`, and bench output.
- **arm64 image build.** If the arm64 build fails on the C++ extension, set `'vllm-fastokens': { platforms: 'linux/amd64', cacheTo: '' }` in the `policy` map of `.github/workflows/build-images.yml` and note in its comment that arm64 dropped because of the arctic extension.
- **FP8 MTP failure.** If `swift-1.5-fp8` fails to boot with MTP, restore the snapshot with the same `docker run` root trick (`os.unlink(p); shutil.copyfile(p + ".orig", p)`), revert step 14, and record the error. If it fails to boot even without MTP, drop it from the matrix.
- **Suffix decoding failure.** If vLLM rejects `method: "suffix"` on this hybrid GDN model (or the `--mamba-cache-mode align` combination), revert step 17's commit and record "unsupported on vLLM 0.30 + Qwen3.8 GDN".
