# qwen3.8-27b-fp8 benchmark record

Numbers are from the live lane on the `ai` host. They exist because the lane's
prefill and spec-decode settings are the two things that decide whether agent
traffic feels fast, and both were re-litigated on 2026-10-01 (prefix caching
re-enabled, DSpark7 adopted) without a record of what each one bought.

## Environment

| | |
|---|---|
| GPU | RTX PRO 5000 Blackwell 72 GB (host `ai`, 192.168.1.98) |
| Engine | `ghcr.io/mspiegel31/vllm-fastokens:latest` → vLLM 0.30.0 |
| Weights | `Qwen/Qwen3.8-27B-FP8`, BF16 KV, FLASHINFER, auto-fit context |
| Flags | `--performance-mode interactivity`, `--max-num-seqs 64`, `--gpu-memory-utilization 0.90` |
| Template | `qwen3.8-froggeric-v22.5.jinja`, thinking off for the benches |
| Client | direct to vLLM inside `llama-swap-vllm-backend` (see caveats) |

## 1. Prefix caching (engine counters, live traffic)

Both rows are the same weights and the same DSpark7 config; only
`--no-enable-prefix-caching` differs.

| prefix caching | hit rate | avg prompt throughput | avg generation throughput |
|---|---|---|---|
| off (17:33–17:44Z) | 0.0% | 2.9K–14.6K tok/s | 45–144 tok/s |
| on (18:12–18:28Z) | 82.2–87.1% | 0–497 tok/s | 31–126 tok/s |

With caching off, every turn re-prefilled its whole context, which is what the
prompt-throughput counter shows: it *is* the prefill, and it disappears once
blocks are reused. GPU KV cache usage stayed at 38–65% of the auto-fit pool
across both.

## 2. Cold vs cached turn time (streamed, 200–320-token answers)

| context | cold TTFT | cached TTFT | cold total | cached total |
|---|---|---|---|---|
| 1.6k | 0.40s | 0.39s | 1.33s | 0.39s¹ |
| 9.6k | 2.08–2.12s | 0.30–0.39s | 3.61s | 2.32s |

¹ 1-token reply in the cached arm; the payload is that prefill vanished.

Derived on this box: prefill ≈ **4.8K tok/s**, so a reused turn saves ≈ **0.18s
per 1k tokens** of context (~5.2s at 30k, ~8.7s at 50k). The cached floor is
~0.3–0.4s of queue plus first token. Decode rate is unaffected by caching — it
is the same 45–60 tok/s either way.

## 3. DSpark7 vs MTP3 (same weights, prompt, client)

9.6k cached prefix, 320-token prose answers, `temperature 0.7`, three or more
runs per config. Production traffic was hitting the lane during the runs, so
quote the spread, not a single number.

| config | decode tok/s | turn total | TTFT | engine mean acceptance length |
|---|---|---|---|---|
| DSpark7 (`num_speculative_tokens 7`) | 47.4 / 48.6 / 52.6 | 6.47–7.13s | 0.39s | 2.11–3.05 |
| MTP3 (`num_speculative_tokens 3`) | 43.8 / 44.3 / 45.9 / 46.7 / 49.8 / 55.7 | 6.03–7.60s | 0.29–0.30s | 2.43–3.57 |
| DSpark7, draft acceptance | — | — | — | 20.0–28.7% |
| MTP3, draft acceptance | — | — | — | 47.7–85.6% |

**Read:** on this workload the two are within run-to-run noise. DSpark drafts
more than twice as many tokens per step but accepts proportionally fewer, and
its per-position acceptance collapses (0.64–0.72 / 0.37–0.51 / … / 0.01–0.14 by
position 7), so the last four draft slots mostly burn compute. The speculator's
model-card advantage (4.4–5.7 mean acceptance) is measured on HumanEval, math
and RAG; free-form prose and agent chatter do not reproduce it. MTP3 costs no
draft VRAM (the head ships in the checkpoint) and leaves the ~3.7 GiB the
speculator occupies for KV.

Untested follow-ups, in rough value order: DSpark with `num_speculative_tokens`
3–4 (drops the dead positions), and the same comparison on a coding task rather
than prose.

## Correctness checks

`canary_prefix_cache.py` probes the reused-prefix corruption class (vllm#53912,
issue #57128 still open in v0.30.0): a context-pinned continuation must decode
identically with and without the cache, a request reusing another request's
decode-written prefix must not surface tokens it never contained, and a
shared-prefix sweep must not degenerate. Last run: `margin_equal`, `no_leak` and
`no_degeneration` all true. That is a smoke result, not proof — the issue's
observed rates are 0.3–0.8% of responses.

## Caveats on method

- **LiteLLM response caching is on** (`litellm_settings.cache: true`, Redis), so
  a repeated identical request body returns without touching the GPU. Any tok/s
  figure measured through the gateway with a fixed prompt is measuring Redis.
- `drop_params: true` on LiteLLM also strips unknown fields, so `cache_salt`
  cannot be controlled through the gateway at all — hence the direct-to-vLLM
  benches.
- The benches' cold arm is forced by a random session nonce, but on a quiet box
  repeated cold runs still came back warm (0.30s TTFT); only the first cold run
  after a config change was reproducibly cold. Treat the cold column as one
  sample.
- Decode numbers move with concurrency: the same config measured 44 tok/s while
  three requests were in flight and 56 tok/s alone.

## Reproducing

```
# spec-decode / prefix-cache bench (needs a container on the backend network)
docker run --rm --network llama-swap-vllm-backend \
  -v "$PWD/bench_spec_decode.py:/bench.py:ro" \
  ghcr.io/mspiegel31/vllm-fastokens:latest python3 /bench.py <label>

# prefix-cache correctness canary
docker run --rm --network llama-swap-vllm-backend \
  -v "$PWD/canary_prefix_cache.py:/canary.py:ro" \
  ghcr.io/mspiegel31/vllm-fastokens:latest python3 /canary.py

# engine-side counters for whatever is currently loaded
docker logs --tail 20 vllm-qwen3-8-27b-fp8
```
