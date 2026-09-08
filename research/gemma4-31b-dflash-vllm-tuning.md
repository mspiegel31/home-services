# Gemma 4 31B NVFP4 and DFlash tuning on RTX PRO 5000 Blackwell

**Investigated:** 2026-09-07

## Decision

Do **not** use `z-lab/gemma-4-31B-it-DFlash` with the repository's stock `vllm/vllm-openai:v0.28.0` image for production. v0.28.0 recognizes the checkpoint and contains much of the later mixed-attention and Model Runner V2 plumbing, but it lacks two Gemma-specific correctness/performance fixes that remain only in open PR #41703:

- Gemma's `sqrt(hidden_size)` target-embedding normalization on the DFlash draft path;
- Gemma's `final_logit_softcapping` in the draft logits processor.

Those omissions do not necessarily make every request crash because target verification can reject bad drafts, but they can collapse acceptance and erase the acceleration. The z-lab card is correct to require PR #41703 for its measured behavior. That PR remains open, stale, and needs rebase, so it also should not be overlaid piecemeal onto v0.28.0.

The safe optimization available on v0.28.0 is Google's **MTP assistant**, `google/gemma-4-31B-it-assistant`. Gemma 4 MTP support merged in vLLM PR #41745 and exists in the v0.28.0 tag. Its NVFP4 target pairing has upstream B300 evidence at seven draft tokens.

Treat DFlash as a later custom-image experiment. First tune the NVIDIA NVFP4 target and MTP on the current image.

## Source evidence

1. [`z-lab/gemma-4-31B-it-DFlash`](https://huggingface.co/z-lab/gemma-4-31B-it-DFlash) is a 3.1 GB BF16 drafter, not a target model. It must be paired with Gemma 4 31B. Its config declares five Qwen3 draft layers, `block_size=16`, four sliding-attention layers, one full-attention layer, and six target auxiliary layers.
2. [vLLM PR #41703](https://github.com/vllm-project/vllm/pull/41703) remains open, stale, and needs rebase. Its branch should not be overlaid onto v0.28.0 because upstream refactors caused conflicts even in May.
3. The v0.28.0 `qwen3_dflash.py` source explicitly names `z-lab/gemma-4-31B-it-DFlash` and supports its mixed sliding/full-attention geometry under `VLLM_USE_V2_MODEL_RUNNER=1`, but the same file contains neither `final_logit_softcapping` nor Gemma embedding normalization.
4. [vLLM PR #41703](https://github.com/vllm-project/vllm/pull/41703) describes those missing pieces as required Gemma4-compatible DFlash behavior. The PR's measured results therefore do not apply to stock v0.28.0.
5. [vLLM PR #41745](https://github.com/vllm-project/vllm/pull/41745) added Gemma 4 MTP and is merged. The v0.28.0 tag contains `gemma4_mtp.py`; upstream reported the NVIDIA 31B NVFP4 target at `K=7` with acceptance length 5.19 and about 296.9 output tok/s on B300.
6. [The vLLM recipe](https://recipes.vllm.ai/Google/gemma-4-31B-it?variant=nvfp4&hardware=b200) lists `nvidia/gemma-4-31B-it-NVFP4`, FP8 KV cache, Gemma reasoning/tool parsers, prefix caching, optional text-only mode, and single-node TP. Its YAML advertises DFlash only for the default target variant; NVFP4 plus z-lab DFlash therefore has no recipe validation.
7. NVIDIA reports small target-only quality deltas for [`nvidia/Gemma-4-31B-IT-NVFP4`](https://huggingface.co/nvidia/Gemma-4-31B-IT-NVFP4): GPQA 85.80→85.35, LiveCodeBench 82.49→82.27, SciCode 33.61→33.18, and unchanged Terminal-Bench Hard.

## Selected deployment

The configured Gemma lane retains the user's current target:

- target: `unsloth/gemma-4-31B-it-NVFP4`;
- vLLM: pinned `0.28.0`;
- native context: 262,144 tokens;
- GPU memory reservation: 0.90;
- KV cache: FP8;
- Gemma reasoning and tool parsers;
- prefix caching through `VLLM_COMMON`;
- Google MTP assistant with four speculative tokens;
- `max-num-seqs=128` inherited from the global default.

The routing policy now uses a matrix. Gemma appears only in its singleton set, so requesting it evicts every other model and requesting another model evicts Gemma. This makes the 0.90 reservation enforceable while preserving the previous small-plus-large co-residency combinations for the remaining models.

## Implemented launch profile

```text
model: unsloth/gemma-4-31B-it-NVFP4
max-model-len: 262144
gpu-memory-utilization: 0.90
kv-cache-dtype: fp8
enable-prefix-caching: true
reasoning-parser: gemma4
tool-call-parser: gemma4
enable-auto-tool-choice: true
speculative-config:
  method: mtp
  model: google/gemma-4-31B-it-assistant
  num_speculative_tokens: 4
```

No `--trust-remote-code` flag is present. The repository forbids it, and vLLM 0.28.0 implements Gemma 4 and Gemma MTP natively.

## MTP tuning note

Start at four draft tokens, then test seven and eight. The upstream NVFP4 B300 run found `K=7` useful, but the RTX PRO 5000 has different bandwidth and kernel behavior. MTP shares target KV and is supported in stock v0.28.0; it does not require Model Runner V2 or a separate draft attention backend.

## Future DFlash custom image

Only after a rebased Gemma DFlash implementation contains PR #41703's normalization and soft-cap fixes, use:

```text
environment: VLLM_USE_V2_MODEL_RUNNER=1
speculative-config:
  method: dflash
  model: z-lab/gemma-4-31B-it-DFlash
  num_speculative_tokens: 7
  attention_backend: flash_attn
target attention backend: triton_attn
```

Do not infer compatibility from successful startup. Require expected acceptance and exact greedy-output parity.

## Speculative-depth sweeps

For MTP, sweep:

```text
num_speculative_tokens: 2, 4, 7, 8
max-num-seqs: 1, 4, 8, 16, 32
max-num-batched-tokens: 16384, 32768
```

For a future corrected DFlash image, sweep `K=4,7,10,15`. Select by end-to-end task time and TPOT, not acceptance rate alone. More draft tokens can raise draft work faster than accepted work.

## Tuning sequence

### Stage 1: establish target correctness

Test the retained Unsloth target with MTP disabled and enabled while holding fixed:

- 262,144-token context;
- 0.90 GPU memory utilization;
- FP8 KV;
- sampling settings;
- tool schemas and prompts;
- concurrency and request order.

Check:

- greedy text outputs;
- thinking on and off;
- one tool call;
- a multi-turn tool call followed by a tool result;
- 20–40 OMP prompts that exercise skill loading and instruction adherence;
- startup VRAM, available KV tokens, TTFT, TPOT, and output tokens/s.

### Stage 2: prove MTP preserves behavior

Run baseline and MTP with greedy decoding. Speculative decoding should preserve target output. Compare final token IDs or exact decoded output for representative text, code, tool, and long-context prompts.

Exercise concurrency values `1, 4, 8, 16, 17, 24, 32`. Reject MTP if any arm produces:

- output divergence under greedy decoding;
- malformed or leaked tool calls;
- reasoning tags in content;
- engine restart, CUDA fault, or NaN;
- zero prefix-cache hits on exact repeated prefixes;
- repeated-call loops absent from the baseline.

Repeat the same suite for DFlash only after building a corrected image. Seventeen remains a deliberate DFlash regression probe because the old PR failed when actual batch size differed from CUDA-graph padded batch size.

### Stage 3: tune speculative depth

Measure `K=4,7,10,15` on three workload shapes:

| Workload | Input | Output | Concurrency |
|---|---:|---:|---:|
| Interactive tool call | 16K | 256 | 1 and 4 |
| Coding agent turn | 16K | 2K | 1, 4, and 8 |
| Agent fanout | 32K shared prefix + unique tails | 1K | 8, 16, and 32 |

Record:

- request throughput;
- output token throughput;
- median and p99 TTFT;
- median and p99 TPOT;
- mean acceptance length;
- per-position acceptance;
- draft versus accepted token throughput;
- peak GPU memory;
- prefix-cache hits;
- task success and valid tool-call rate.

The z-lab B300 results suggest acceptance length around 4.2 for chat, 6.1 for MBPP, and 7.5–8.6 for math/code at `K=15`. The RTX PRO 5000 and NVFP4 target should not be expected to reproduce B300 throughput or acceptance.

### Stage 4: context and cache

The selected profile requires the full 262,144-token context. Validate that startup reports a KV pool large enough for one full-length request after loading the target, assistant, vision tower, and CUDA graphs. Failure to provide one complete request slot is a configuration failure rather than a reason to silently lower context.

Keep FP8 KV and prefix caching enabled in production because OMP repeats a large system/tool prefix. For isolated synthetic throughput benchmarks, disable prefix caching to prevent warm-cache contamination.

### Stage 5: residency

The selected 0.90 allocation requires Gemma to run alone. The matrix routing policy enforces that invariant while retaining the prior co-residency combinations for the remaining model families.

### Stage 6: text-only versus vision

For OMP coding and tool runners, `--language-model-only` is the cleanest memory optimization. It frees the vision tower and leaves more room for KV cache and graphs. Expose it under a distinct text-only model ID so clients are not told that vision is available.

If vision remains required, keep the encoder and cap image count/resolution. Gemma supports visual token budgets of 70, 140, 280, 560, and 1120 per image. Start at 280.

### Stage 7: scheduler and graphs

Only after the DFlash baseline is stable:

1. compare balanced versus throughput performance mode;
2. compare default scheduling with `--async-scheduling` if v0.28 accepts it with DFlash;
3. keep CUDA graphs enabled unless an actual capture OOM or correctness bug appears;
4. tune `max-num-seqs` to the real concurrency distribution, not the recipe's B200/B300 table.

Change one knob per arm. DFlash, async scheduling, context size, cache dtype, and performance mode all affect memory or scheduling; enabling them together makes failures uninterpretable.

## Expected outcome

The current NVFP4 target plus Google's MTP assistant should fit within the 0.90 reservation at 262K with FP8 KV, but startup must prove that one full-length sequence fits after graph capture. The uncertain variable is MTP acceptance against this specific community quant. A measurable end-to-end improvement with exact greedy-output parity justifies keeping MTP.

## Next tuning steps

1. Validate the expanded llama-swap matrix configuration.
2. Launch Gemma and confirm the reported model length, target/draft load, KV capacity, and 0.90 allocation.
3. Smoke-test reasoning, tools, and a complete OMP skill workflow.
4. Compare MTP on and off at identical settings.
5. Sweep MTP K only after the four-token profile passes correctness and stability checks.
