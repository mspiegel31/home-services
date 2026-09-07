# vLLM Qwen3.8 DFlash2 and prefix-cache tuning

## Decision

Keep DFlash2 on vLLM `v0.28.0` and disable `FlashInferFP8ScaledMMLinearKernel` for this SM120 checkpoint. The `num_speculative_tokens=7` setting matches both the [official vLLM Qwen3.8 recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B) and the [DFlash2 model card](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2). Keep `--max-num-seqs 128`, `--gpu-memory-utilization 0.9`, FP8 E4M3 KV, prefix caching, and throughput mode.

For the expected case where the card reports at least 70 GiB, make the resolved token budget explicit:

```text
--max-model-len auto
--gpu-memory-utilization 0.9
--kv-cache-dtype fp8_e4m3
--enable-prefix-caching
--max-num-seqs 128
--max-num-batched-tokens 16384
--performance-mode throughput
--speculative-config '{"method":"dflash","model":"incoai/Qwen3.8-27B-DFlash2","num_speculative_tokens":7}'
```

**Inference:** `--max-num-batched-tokens 16384` does not change the expected `v0.28.0` behavior if the server reports at least 70 GiB of device memory. It records a value that vLLM otherwise derives from GPU memory, usage context, and throughput mode. Confirm the resolved value in the startup log because the 72 GB product label does not prove the byte threshold and the local profile uses a mutable custom image tag.

Do not replace DFlash2 with native MTP on `v0.28.0`. Open upstream reports cover native-MTP CUDA illegal-memory-access failures on hybrid GDN models, including Qwen3.8 on SM120, and prefix-cache loss with speculative decoding. The relevant Mamba state-copy race fix missed the `v0.28.0` branch cut.

The production change adds `VLLM_DISABLED_KERNELS=FlashInferFP8ScaledMMLinearKernel`. Upstream issue [#52540](https://github.com/vllm-project/vllm/issues/52540) traces sustained-load SM120 wedges to this lane. The local canary improved eight-request aggregate throughput by 17.9% and isolated decode by 1.2%, while reducing full-context KV concurrency from 2.86x to 2.80x.

The remaining resource candidates are not justified by the observed workload:

1. `--max-num-batched-tokens 32768` could improve long-prefill scheduling, but the resolved 16,384-token control already delivered 1,182.655 aggregate output tokens/s at eight-way concurrency.
2. `--gpu-memory-utilization 0.92` only expands cache capacity and reduces the current safety margin; the control had zero preemptions.
3. `--max-num-seqs 64` is useful only if the 128-sequence profile shows pressure or unstable tail latency.

## Evidence labels

This note uses three labels:

- **Fact:** stated in cited documentation, source, issue data, or the checked-in local profile.
- **Local fact:** present in this repository or supplied as an observed property of the deployment.
- **Inference:** a conclusion from those facts that still needs a local measurement.

## Why vLLM uses 7 while SGLang uses an 8-token block

The two settings describe the same DFlash2 geometry with different counters.

- **Fact:** The DFlash2 checkpoint uses a speculation block size of 8 and produces 7 draft tokens per target verification step. The [model card](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2) states both values explicitly.
- **Fact:** vLLM configures the number of speculative candidates, so its official command uses `num_speculative_tokens: 7`.
- **Fact:** SGLang configures the DFlash verification block, so its official Qwen3.8 command uses `--speculative-num-draft-tokens 8`. The [SGLang cookbook](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B) calls 8 the draft block size and includes it in the speculative GDN-state reservation.
- **Fact:** When all 7 candidates are accepted, target verification can also yield the next target token. This makes the maximum number of output tokens from a verification round 8.

Do not change vLLM to `num_speculative_tokens=8` to mirror the SGLang spelling. That would ask vLLM for eight speculative candidates and would no longer match the published vLLM DFlash2 profile.

## DFlash2 versus native MTP

| Property | DFlash2 | Native MTP |
|---|---|---|
| Draft source | Separate `incoai/Qwen3.8-27B-DFlash2` checkpoint | Prediction head embedded in the target checkpoint |
| Proposal method | One block-diffusion draft pass, local depthwise convolution, then a candidate-path selector | Successive future-token predictions from the model's MTP modules |
| Official vLLM Qwen3.8 depth | 7 speculative candidates | 3 speculative tokens in the current recipe |
| Extra weights | Yes | No separate draft checkpoint |
| Verification | Target model verifies proposed tokens; DFlash2 reports lossless greedy and distribution-preserving sampled decoding | Target model verifies proposed tokens |
| Upstream `v0.28.0` status | First supported release through [PR #52816](https://github.com/vllm-project/vllm/pull/52816); forces Model Runner V2 | Supported syntax, but affected by open hybrid-GDN safety reports |
| Current deployment decision | Keep | Do not deploy on `v0.28.0` |

DFlash2 predicts all block positions together. Its dynamic convolution lets later positions see earlier positions in the proposed block, and its selector chooses a coherent path from per-position candidates. Native MTP carries less checkpoint overhead, but each additional prediction step consumes target-side work and recurrent-state handling. Acceptance, draft cost, target verification cost, batch size, and prompt type determine which is faster.

The DFlash2 authors report strong H200 results, including declining speculative benefit as concurrency rises. Those measurements establish that DFlash2 can work well. They do not predict throughput on an RTX PRO 5000 Blackwell with this quantized target, FP8 E4M3 KV, and agent traffic.

## Audit of the checked-in vLLM profile

The local profile is defined in [`services/llama-swap-vllm/config.yaml`](../services/llama-swap-vllm/config.yaml).

| Local setting | Exact `v0.28.0` meaning | Comparison with official guidance | Decision |
|---|---|---|---|
| `RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead` | NVFP4 target with BF16 embedding and language-model head | The recipe demonstrates other Qwen3.8 checkpoints. DFlash2 targets the same base model family. | Keep the locally validated target. Do not transfer memory figures from another export. |
| `--max-model-len auto` | Select the model maximum if it fits; otherwise select the largest length the profiled GPU cache can hold. | The recipe pins `262144`. | Keep `auto` for fit safety. Record the resolved context length and KV capacity at startup. |
| `--gpu-memory-utilization 0.9` | Caps the model executor's per-instance GPU-memory budget. `v0.28.0` defaults to `0.92`. | The recipe does not establish a safe value for this checkpoint and GPU. | Keep `0.9` as the production margin. Canary `0.92` separately. |
| `--kv-cache-dtype auto` | Resolves from the checkpoint's `kv_cache_scheme`. The tested RadixArk checkpoint resolves to FP8 E4M3, not BF16, and vLLM warns that missing calibration data leaves the KV scale at `1.0`. | The official recipe recommends FP8 KV for its sample checkpoints. | Make the resolved `fp8_e4m3` value explicit to preserve current performance and capacity. Treat BF16 KV as a separate quality canary, not a silent assumption about `auto`. |
| `--enable-prefix-caching` | Enables hash-based APC. On hybrid recurrent models, vLLM resolves Mamba/GDN cache mode to `align` by default. | `v0.28.0` also enabled prefix caching by default for Mamba models. | Keep the explicit flag. Measure hits because speculation can reduce them on this version. |
| `--max-num-seqs 128` | Hard cap on sequences scheduled in one iteration. | On a GPU reporting at least 70 GiB, vLLM's API-server default is 1024 before throughput mode. That generic default does not account for this deployment's chosen safety envelope. | Keep 128. It already exceeds the `v0.28.0` SM120 default graph-capture ceiling for K7 decode shapes. |
| `--performance-mode throughput` | Doubles derived `max_num_batched_tokens` and `max_num_seqs` values when the corresponding flag was omitted. Explicit values are not doubled. Its CUDA-graph size list otherwise follows the same branch as balanced mode; interactivity mode is the distinct fine-grained branch. | Appropriate for testing aggregate token rate at high concurrency. | Keep. Do not treat it as a substitute for explicit scheduler budgets. |
| no explicit `--max-num-batched-tokens` | **Inference:** If the GPU reports at least 70 GiB, the API-server base is 8192 and throughput mode doubles it to 16384. Below that threshold, the base is 2048 and throughput mode produces 4096. | The tuning guide recommends more than 8192 for throughput on large GPUs. | Read the resolved startup value. Use 16384 as the control only when the server confirms it; otherwise add it as the first measured canary. |
| DFlash2 K7 | Seven candidates per verification step. | Exact match with the official vLLM recipe. | Keep. |

### Local control measurements

The live control used `ghcr.io/mspiegel31/vllm-fastokens:latest` with vLLM `0.28.0`, build commit `2cf0a6915ce544dc493a0990f2ea38d81601128a`, and Transformers `5.15.1`.

- Startup resolved `max_model_len=262144`, `max_num_batched_tokens=16384`, FP8 E4M3 KV, and `mamba_cache_mode=align`.
- Hybrid page alignment raised the attention block to 1,648 tokens. The server allocated 33.8 GiB for 748,485 KV tokens, enough for 2.86 full-context requests.
- Eight isolated 2,048-token sequential decodes averaged 277.253 output tokens/s, with median 277.752, minimum 271.283, and maximum 281.578.
- DFlash accepted 14,355 of 14,784 draft tokens across the control work, a 97.1% draft-token acceptance rate. Sustained per-window mean acceptance lengths were 7.64 to 7.93 output tokens.
- A 58.8K-token shared-prefix probe reduced time to first token from 12.414 seconds cold to 1.018 and 1.010 seconds warm. Engine metrics recorded 112,064 local cache-hit tokens over 177,561 queried prompt tokens; the two warm requests accounted for those hits.
- Disabling `FlashInferFP8ScaledMMLinearKernel` produced 280.465 mean isolated decode tokens/s, up 1.2% from control. Eight simultaneous 1,024-token requests completed at 1,394.052 aggregate output tokens/s versus 1,182.655 for control, a 17.9% gain.
- The canary used 33.2 GiB for 735,256 KV tokens, 1.8% fewer than control, and retained 2.80 full-context requests.
- Against the matched SGLang K8 measurements, vLLM control was 3.9% faster sequentially and 54.0% faster at eight-way concurrency. The tuned vLLM canary was 5.1% and 81.5% faster, respectively. These are local workload results, not an engine-wide ranking.

The managed control traversed LiteLLM and llama-swap; the temporary canary used a direct host port. The isolated `generationTps` comparison excludes most request-start overhead, but the aggregate wall-rate comparison can include proxy cost. Treat 17.9% as a strong promotion signal alongside the #52540 safety case, not as a fully isolated kernel microbenchmark.

These measurements confirm that K7 DFlash and APC both work on the current image. They do not remove the FP8 unit-scale quality risk or the mutable-image reproducibility risk.

### Why 128 sequences already exceeds the SM120 graph ceiling

`v0.28.0` computes a default CUDA graph size from `max_num_seqs * (1 + num_speculative_tokens) * 2`. Its 1024-token special case applies to CUDA capability family 10.x. SM120 is family 12.x and follows the 512-token fallback unless a platform override or explicit compilation setting changes it. With K7, 128 sequences produce an uncapped value of 2048 and 64 sequences produce 1024, so both reach the same 512-token default ceiling. Raising `max-num-seqs` above 128 cannot increase that ceiling, though it can admit more work and consume more recurrent state. This makes 256 a poor blind canary.

## vLLM APC and SGLang RadixAttention

Both systems reuse model state from prior requests with the same token prefix. Their indexes and hybrid-state policies differ.

| Dimension | vLLM automatic prefix caching | SGLang RadixAttention |
|---|---|---|
| Primary index | Hash table keyed by chained block hashes | Compressed radix tree keyed by token sequences |
| Key contents | Parent-block hash, exact token tuple, and optional LoRA, multimodal, prompt-embedding, and cache-salt data | Token IDs plus namespace data such as `extra_key` and `cache_salt`; each tree edge stores a token span |
| Normal lookup unit | Full hash units. The `v0.28.0` cache-block default is 16 tokens, while hybrid group alignment can resolve to a much larger scheduler block. `prefix_match_unit` can permit finer hash boundaries when every group supports them. | Page-aligned token spans. The documented default `--page-size` is 1, so ordinary radix lookup can split at token boundaries. |
| Hybrid lookup | Query each cache group, then use an iterative fixed-point reconciliation to find a prefix available to every required group | Traverse the longest token path, then return the deepest usable node that also owns a recurrent-state checkpoint |
| Scheduling | APC reports already-computed blocks to the scheduler; chunked prefill is decode-first and consumes the remaining token budget | `--schedule-policy lpm` sorts waiting requests by longest cached prefix; in-batch prefix logic can delay siblings so one request materializes a shared prefix first |
| In-use protection | Block reference counts; a hit removes a zero-reference block from the free eviction queue | Lock references protect the matched path and terminal recurrent state |
| Default eviction | LRU-like free-block queue. Allocation evicts the cached block at the queue head. Freed cached blocks return to the queue tail. | LRU radix-leaf eviction by default; LFU, SLRU, and priority policies are also available |
| Recurrent-state eviction | Recurrent entries use the same block pool and group-aware cache coordinator | Full-attention KV and Mamba/GDN checkpoints have separate LRU lists. An internal checkpoint can become a tombstone while the full-KV radix path remains. |
| Cross-request scope | Reuse within one engine instance and compatible cache namespace. Cross-instance reuse needs a connector or offload configuration. | Reuse within one inference instance. HiCache L1 and L2 remain instance-private; configured L3 storage can share across instances. |

### vLLM: chained hashes and a common hybrid boundary

For each full hash unit, vLLM hashes the preceding block hash, this unit's exact token IDs, and any identity-changing extras. The parent hash makes the key represent the complete prefix rather than a matching token fragment in the middle of another sequence. The scheduler looks up computed blocks before allocation, increments references on hits, and protects those blocks from eviction.

Qwen3.8 complicates the ordinary block story. Sixteen layers store full-attention K/V for every token. Forty-eight GDN layers compress the whole processed prefix into recurrent state plus convolution state. A GDN checkpoint cannot be sliced to reconstruct an arbitrary earlier prefix. `v0.28.0` therefore groups cache types, aligns physical page sizes, and reconciles their hit lengths. A prefix is reusable only where both the full-attention K/V and a compatible GDN checkpoint exist.

With APC enabled, `mamba_cache_mode=align` stores GDN state at scheduler-step and block boundaries while keeping a sparse set of resident state blocks. Speculative decoding adds lookahead state and changes the alignment geometry. The exact reusable unit must be read from the resolved cache configuration or measured from hit deltas. It is unsafe to assume that the visible 16-token attention block is the Qwen3.8 prefix-hit unit.

### SGLang: token paths plus terminal recurrent checkpoints

SGLang's radix tree stores a consecutive token span in each node. Lookup walks the longest matching path and splits a node when a match ends inside its span. With the default one-token page, the tree can represent fine token boundaries and shared branches directly.

For a hybrid model, each node can hold two different resources:

1. Full-attention KV indices for the complete matched path.
2. One Mamba/GDN state checkpoint representing the whole prefix at that node.

The recurrent checkpoint cannot be split when a radix edge is split. SGLang therefore selects the deepest matched node with a live checkpoint, reuses full K/V along the path to that node, and copies or donates the terminal recurrent state into the request's active slot. The `extra_buffer_lazy` strategy used by the local SGLang profile lowers checkpoint-buffer demand by donating a tracked state lazily. Its benefit and memory accounting are SGLang-specific; it is not a vLLM flag.

### Lookup and scheduling consequences

A vLLM hash lookup has direct block-key access and no tree traversal. Its useful Qwen3.8 hit can still fall back substantially when one hybrid group lacks state at the candidate boundary. SGLang's tree makes longest-prefix structure explicit, and LPM can reorder queued work around those matches. The tree, node splitting, lock accounting, and recurrent checkpoint pool add metadata and state-management work.

The checked-in SGLang lane opts into `--schedule-policy lpm`; the vLLM lane has no matching LPM flag. This difference matters for a queue of agent requests sharing a long system prompt. It does not establish that RadixAttention is universally faster. At more than 128 waiting requests, current SGLang source falls back from LPM to FCFS to avoid the matching and sorting cost.

### Eviction and reuse consequences

Both engines retain completed-request state until memory pressure reclaims it. In-use entries are protected by references or locks.

vLLM's free queue prefers evicting less reusable request tails. SGLang normally evicts unlocked LRU leaves, then exposes parents as new leaf candidates. Its hybrid cache can evict an internal recurrent checkpoint independently, preserving the full-KV tree as a tombstoned path. A later request may match those tokens but must fall back to an earlier node with a live GDN checkpoint.

Neither local GPU cache is shared between independent server processes. Prefix reuse across requests means requests handled by the same engine instance with compatible model state, tokens, multimodal inputs, adapters, and cache salt.

### Performance consequences

Prefix caching removes repeated prefill work. Its primary signals are cached prompt tokens and time to first token. It does not make autoregressive target decoding faster after the cached prefix.

DFlash2 attacks the decode phase by producing several candidates per target verification. A workload can benefit from both features: APC skips a repeated agent prefix, then DFlash2 shortens the subsequent decode. The two optimizations also interact through GDN state alignment on `v0.28.0`, so enabling both does not guarantee that either retains its standalone gain.

## `v0.28.0` hazards

### Native MTP safety

[vLLM issue #53726](https://github.com/vllm-project/vllm/issues/53726) reports illegal-memory-access failures in hybrid GDN plus native MTP. Follow-up data includes Qwen3.8 NVFP4 on RTX 5090 SM120 and failures with one running request. Disabling async scheduling did not establish a reliable fix.

[vLLM PR #50729](https://github.com/vllm-project/vllm/pull/50729) fixes overlapping convolution-state copies during speculative decoding. Upstream issue discussion records that it missed `v0.28.0` and first appeared in the `v0.28.1` release-candidate line. That fix is necessary evidence for an upgrade canary, but it does not close every crash mechanism discussed in #53726.

**Decision:** native MTP remains out of scope for production until a newer pinned build passes a long SM120 soak across recurrent-state boundaries.

### Prefix-cache loss with speculation

[vLLM issue #54360](https://github.com/vllm-project/vllm/issues/54360) reports partial or zero prefix hits when hybrid GDN prefix caching is combined with MTP or DFlash. A Qwen3.8 DFlash2 K7 data point on a pre-release branch reached a lower plateau than no-speculation APC. Tagged `v0.28.0` MTP data shows a repeatable one-alignment-unit loss on another hybrid Qwen model. The issue also documents two observability traps:

- The hash/alignment unit changes with speculative depth, so raw hit counts cannot be compared without recording the resolved geometry.
- `usage.cached_tokens` can stay zero while engine metrics report real hits. Use `vllm:prefix_cache_hits_total` and `vllm:prefix_cache_queries_total`.

[PR #52244](https://github.com/vllm-project/vllm/pull/52244) attempts to repair related MTP boundary behavior but remains open, targets the MTP/EAGLE path, and has conflicting follow-up measurements. `--prefix-match-unit` is therefore not a safe workaround to add blindly to this DFlash2 deployment.

### First-release and image identity risk

DFlash2 entered vLLM in `v0.28.0` and forces Model Runner V2. The support PR fixed correctness and concurrency findings during review, but first-release coverage warrants a production-length soak.

The repository pins the stock `v0.28.0` image digest globally, while this model overrides it with `ghcr.io/mspiegel31/vllm-fastokens:latest`. Record the effective image digest, base commit, vLLM version, Transformers version, CUDA version, and FlashInfer version for every canary. A mutable tag makes two nominally identical runs incomparable.

## Tuning decision table

| Candidate | Exact delta from the recommended control | Status | Expected signal | Main risks and rejection rule |
|---|---|---|---|---|
| Explicit current token budget | `--max-num-batched-tokens 16384` | Adopt for reproducible tests | No material performance change if the inferred resolved value is correct | Reject the inference if startup reports another resolved value; use the reported value as control. |
| Disable the affected SM120 FP8 linear kernel | `VLLM_DISABLED_KERNELS=FlashInferFP8ScaledMMLinearKernel` | Adopt | Avoid the sustained-load wedge in #52540 and improve concurrent throughput | Local canary: +17.9% aggregate at eight requests, +1.2% isolated decode, and 1.8% lower KV-token capacity. |
| Larger scheduling batch | `--max-num-batched-tokens 32768` | Defer | Higher prompt throughput or aggregate output throughput when long prefills leave the GPU underfilled | More activation/workspace pressure, worse decode ITL, startup or runtime OOM, increased tail latency. The measured workload did not establish a need beyond 16384. |
| Higher executor memory budget | change `--gpu-memory-utilization 0.9` to `0.92` | Defer | Larger KV pool and fewer preemptions. **Inference:** two percentage points on a nominal 72 GB card expose about 1.44 GB more executor budget before overhead. | Less headroom for CUDA graphs, allocator variance, driver use, or another process. The control had zero preemptions. |
| Lower sequence cap | change `--max-num-seqs 128` to `64` | Conditional safety canary | Same default SM120 capture ceiling at K7, lower live-state pressure, possibly better p99 under a target load of at most 64 concurrent requests | Caps throughput above 64 active requests. Promote only if the 128 arm preempts, fails, or loses goodput at the real arrival rate. |
| BF16 KV | `--kv-cache-dtype bfloat16` | Quality canary only | Avoids the uncalibrated FP8 unit scale and may improve accuracy | Roughly doubles attention KV storage and can reduce long-context concurrency. Do not mix this quality/capacity decision into a decode-throughput canary. |
| Native MTP | replace the DFlash config with `{"method":"mtp","num_speculative_tokens":3}` | Reject on `v0.28.0` | No separate draft checkpoint | Open SM120/hybrid-GDN safety and cache defects. Reconsider only on a fixed pinned build. |
| Different DFlash depth | change K7 | Reject without a new checkpoint or upstream recipe | None established | K7 is the checkpoint's published vLLM geometry. K8 is a SGLang accounting value, not a vLLM tuning hint. |
| Fine prefix unit | add `--prefix-match-unit N` | Defer | Finer potential hit boundary | `N` must divide every cache-group block size, changes metadata and alignment work, and intersects an open speculative-GDN bug. Wait for an upstream fix and model-specific guidance. |
| Higher sequence cap | `--max-num-seqs 256` | Reject as a blind canary | More admission capacity if recurrent state and KV are abundant | No larger default graph ceiling than 128, more state pressure, and no evidence that 128 limits current goodput. |
| Non-cryptographic cache hash | `--prefix-caching-hash-algo xxhash` | Reject for this pass | Lower CPU hash cost if hashing is proven hot | Extra dependency plus collision and trust-boundary concerns; no evidence that SHA256 is the bottleneck. |

Change one resource control at a time. Combining `32768`, `0.92`, and a different sequence cap would prevent attribution and could hide an unsafe memory interaction.

## Benchmark matrix

### Configurations

| ID | Purpose | Flags relative to the recommended control |
|---|---|---|
| A | Production control | DFlash2 K7, APC on, batch tokens 16384, sequences 128, memory 0.90 |
| B | Autoregressive decode control | Omit `--speculative-config`; keep every other A flag |
| C | Prefix-cache diagnostic | A plus `--no-enable-prefix-caching`; do not treat this as a deployment candidate |
| D | Larger-batch canary | A with `--max-num-batched-tokens 32768` |
| E | Memory canary | Winner of A/D with `--gpu-memory-utilization 0.92`; run on an exclusive GPU |
| F | Lower-state-pressure canary | Winner of A/D with `--max-num-seqs 64`; use only if A shows pressure or the target concurrency is at most 64 |

Do not include native MTP in the `v0.28.0` matrix. Run it only in a future fixed-version safety qualification.

### Workload cells

Use the same prompt corpus, sampling settings, seed policy, and request order for every arm. Preserve the production mix of reasoning effort, tool schemas, and structured responses.

1. **Decode acceptance:** input lengths 2K and 16K; output lengths 256 and 2048; concurrencies 1, 8, 32, 64, and 128 where the profile permits. Compare A with B.
2. **Long-prefill scheduling:** input lengths 16K and 64K; output length 256; concurrencies 8, 32, and 64. Compare A with D.
3. **Long decode and state-boundary soak:** input length 16K; output length at least 4096; mixed request completion times; concurrencies 1, 8, and 32. Repeat long enough to cross multiple recurrent-state boundaries.
4. **Exact-repeat cache probe:** send a cold prompt, then replay its exact token IDs at least twice. Test a 16K shared prefix with a 512-token unique tail and several prompt lengths around each observed hit boundary.
5. **Agent fanout:** one long common system/tool prefix, distinct user tails, and concurrent arrivals. Test both an empty cache and a warmed cache.
6. **Unique-prefix control:** same lengths and arrival pattern as agent fanout, with no shared prefix. This separates scheduler and DFlash effects from APC.

The exact-repeat probe should use token IDs or `/tokenize` results rather than approximate word counts. Once the observed hit quantum is known, include lengths at boundary minus 1, boundary, boundary plus 1, and the same offsets around several multiples. That exposes boundary-dependent zero-hit behavior described in #54360.

### Metrics

Record, at minimum:

- Aggregate output tokens per second and prompt tokens per second.
- Per-request output tokens per second.
- TTFT, TPOT/ITL, and end-to-end latency at p50, p95, and p99.
- `vllm:spec_decode_num_drafts_total`, `vllm:spec_decode_num_accepted_tokens_total`, and `vllm:spec_decode_num_draft_tokens_total`. Compute mean accepted output length as `1 + accepted / drafts`, including the target bonus token, and draft acceptance rate as `accepted / draft_tokens`.
- `vllm:prefix_cache_queries_total` and `vllm:prefix_cache_hits_total`, reported as deltas per request and hit ratio.
- KV-cache usage, running and waiting requests, preemption count, and queue time.
- Startup-reported KV capacity, resolved maximum model length, cache group sizes, hash unit, graph capture sizes, and scheduler budgets.
- GPU memory at idle, after graph capture, and at peak load.
- HTTP failures, engine restarts, CUDA errors, NaNs, repeated-token garbage, and incomplete tool calls.

Do not use `usage.cached_tokens` as the cache oracle on this version.

### Promotion gates

A candidate can replace A only when all gates pass:

1. Greedy outputs match the autoregressive control token for token on a representative deterministic set. Sampled runs retain the target quality and tool-call success rate.
2. No illegal memory access, OOM, NaN, malformed output, silent engine exit, or restart occurs during the boundary soak.
3. DFlash acceptance remains stable across repetitions and target traffic classes.
4. Repeated-prefix tests show explainable, nonzero hit deltas across boundary offsets. Any zero-hit geometry is documented before deployment.
5. The candidate improves the production objective, aggregate goodput under the target concurrency, across repeated runs without violating the existing p95/p99 TTFT and ITL limits.
6. The gain survives a unique-prefix control and a warmed shared-prefix workload. This prevents an APC artifact from being credited to batching or speculation.
7. Results include confidence intervals or run-to-run spread. A single fastest run is insufficient.

## Recommended rollout sequence

1. Pin the effective custom image digest and record its component versions.
2. Start with profile A and make the 16384 token budget explicit.
3. Run A, B, and C to measure DFlash decode value and the actual APC penalty independently.
4. Run D against A. Stop if memory, correctness, or tail-latency gates fail.
5. Run E only with the D/A winner on an exclusive GPU.
6. Run F only if the 128-sequence arm shows pressure or production never exceeds 64 concurrent requests.
7. Keep DFlash2 K7 unless a canary proves that autoregressive decoding has better goodput for the real high-concurrency mix.
8. Revisit native MTP after upgrading beyond `v0.28.0`, confirming the overlap-copy fix is present, and closing the SM120 boundary soak and prefix-cache gates.

## Sources

### vLLM

- [Official Qwen3.8-27B recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [vLLM `v0.28.0` serve arguments](https://docs.vllm.ai/en/v0.28.0/cli/serve/)
- [vLLM `v0.28.0` optimization guide](https://docs.vllm.ai/en/v0.28.0/configuration/optimization/)
- [vLLM `v0.28.0` release notes](https://github.com/vllm-project/vllm/releases/tag/v0.28.0)
- [Automatic Prefix Caching design](https://docs.vllm.ai/en/v0.28.0/design/prefix_caching/)
- [`v0.28.0` cache configuration source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/config/cache.py)
- [`v0.28.0` batch-default and throughput-mode source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/engine/arg_utils.py)
- [`v0.28.0` performance-mode and CUDA-graph source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/config/vllm.py)
- [`v0.28.0` CUDA capability-family source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/platforms/interface.py)
- [`v0.28.0` hybrid cache coordinator source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/v1/core/kv_cache_coordinator.py)
- [`v0.28.0` block-pool source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/v1/core/block_pool.py)
- [`v0.28.0` cache-spec source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/v1/kv_cache_interface.py)
- [`v0.28.0` speculative-decoding metrics source](https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/v1/spec_decode/metrics.py)
- [DFlash2 support PR #52816](https://github.com/vllm-project/vllm/pull/52816)
- [Hybrid GDN native-MTP crash issue #53726](https://github.com/vllm-project/vllm/issues/53726)
- [Speculative hybrid prefix-cache issue #54360](https://github.com/vllm-project/vllm/issues/54360)
- [Overlapping Mamba state-copy fix #50729](https://github.com/vllm-project/vllm/pull/50729)
- [Open hybrid GDN prefix-boundary fix #52244](https://github.com/vllm-project/vllm/pull/52244)

### DFlash2 and SGLang

- [Qwen3.8 DFlash2 model card](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2)
- [DFlash2 design and release post](https://inco.ai/blog/dflash2/)
- [SGLang Qwen3.8-27B cookbook](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B)
- [SGLang server arguments](https://docs.sglang.io/advanced_features/server_arguments.html)
- [SGLang radix-cache source](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/radix_cache.py)
- [SGLang hybrid Mamba radix-cache source](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/mamba_radix_cache.py)
- [SGLang scheduling-policy source](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/schedule_policy.py)
- [SGLang HiCache design and sharing scope](https://docs.sglang.ai/advanced_features/hicache_design.html)
