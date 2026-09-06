# Qwen3.8 MTP versus DFlash2

## Decision

Keep DFlash2 as the primary SGLang speculative decoder. The best available same-model, same-architecture evidence shows tuned DFlash2 is faster than the native MTP head on Blackwell SM120. Treat MTP as a lower-memory, no-extra-checkpoint fallback rather than the throughput choice.

Do not enable native MTP in the current vLLM `v0.28.0` deployment. The release supports the configuration syntax, but open hybrid-GDN/MTP defects make it unsafe on this host.

## Evidence

### SGLang measurements

SGLang's Qwen3.8-27B cookbook validates the NVFP4 BF16-lm-head checkpoint on RTX 5090 and RTX PRO 6000. Its RTX 5090, concurrency-one measurements report:

| Decoder | Configuration | Result |
|---|---|---:|
| DFlash2 | 8 draft tokens, BF16 GDN state | 4.92 ms median TPOT, 4.29 accepted tokens/round, approximately 203 output tok/s |
| Native MTP / EAGLE | 3 steps, top-k 1, 4 draft tokens, FP32 GDN state | 152.9 output tok/s/user |
| Native MTP / EAGLE | 3 steps, top-k 1, 4 draft tokens, BF16 GDN state | 144.5 output tok/s/user |

On that operating point, DFlash2 is approximately 33% faster than the faster MTP result and 41% faster than the BF16-state MTP result.

The local RTX PRO 5000 canary confirmed the direction. Eight isolated, sequential, thinking-disabled requests used the same numbered-sequence prompt and a 2,048-token output cap:

| Local profile | Mean output tok/s | Median output tok/s |
|---|---:|---:|
| DFlash2 K=4, concurrency 16, 64 Mamba slots | 136.384 | 136.465 |
| DFlash2 K=8, concurrency 8, 32 Mamba slots | 266.966 | 267.593 |

K=8 improved mean throughput by 95.7%. Seven runs produced 2,048 tokens and one ended normally at 1,815 tokens. Server logs showed acceptance reaching 8.00 tokens/round after warmup.

The K=8 server completed CUDA graph capture with 2.37 GB available GPU memory. Eight simultaneous 1,024-token client streams then completed without errors or OOMs, producing 768.220 aggregate output tok/s. The original K=4 server was restored and verified after the canary.

### What the NInfer result proves

NInfer's raw engine step rate in the supplied benchmark remains near the non-speculative vLLM rate. Its throughput gain therefore comes from accepted MTP proposals. That establishes that MTP is effective, not that MTP is faster than DFlash2.

The NInfer model card also shows that MTP acceptance is workload-dependent: code and structured output accept substantially more proposals than story generation. A single 76% acceptance figure should not be generalized across agent traffic.

### Portability

SGLang can use the checkpoint's embedded MTP head without a separate draft model:

```text
--speculative-algorithm EAGLE
--speculative-num-steps 3
--speculative-eagle-topk 1
--speculative-num-draft-tokens 4
--enable-linear-replayssm-spec
```

`NEXTN` is an alias for `EAGLE`. The local pinned SGLang image contains the Qwen3.5/Qwen3.8 MTP loader and accepts these server arguments.

vLLM `v0.28.0` also exposes native MTP:

```text
--speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

Do not deploy it on the current lane. vLLM issue #53726 reports CUDA illegal-memory-access failures for hybrid GDN plus native MTP on SM120, including Qwen3.8 NVFP4. The current `v0.28.0` image predates the related copy-race fix merged for `v0.28.1rc0`. Issue #54360 separately reports prefix-cache hit loss under native MTP on the hybrid model.

## Recommendation

1. Deploy DFlash2 K=8 with `--max-running-requests 8` and `--max-mamba-cache-size 32`.
2. Keep the existing attention, KV-cache, prefill, context, radix-cache, parser, and FP32 GDN-state settings.
3. Monitor acceptance and tail latency under mixed agent traffic; the local throughput prompt was deliberately highly predictable.
4. Test BF16 GDN state separately if more concurrency is required. It changes numerical behavior and should not be bundled into this throughput cutover.
5. Revisit vLLM MTP after moving past `v0.28.0` and verifying both the SM120 crash fix and prefix-cache behavior.

## Sources

- [SGLang Qwen3.8-27B cookbook](https://github.com/sgl-project/sglang/blob/febb360519875d95dfc25997a7e7d73ba1dc8377/docs/cookbook/autoregressive/Qwen/Qwen3.8-27B.mdx)
- [SGLang Qwen3.8 deployment configuration and measurement annotations](https://github.com/sgl-project/sglang/blob/febb360519875d95dfc25997a7e7d73ba1dc8377/docs/src/snippets/configs/Qwen/qwen3.8-27b.jsx)
- [RadixArk Qwen3.8-27B NVFP4 BF16 LM-head model card](https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead)
- [NInfer Qwen3.8-27B artifact model card](https://huggingface.co/neroued/Qwen3.8-27B-nvfp4-NInfer)
- [vLLM issue #53726: hybrid GDN native-MTP CUDA illegal memory access](https://github.com/vllm-project/vllm/issues/53726)
- [vLLM issue #54360: native-MTP prefix-cache regression](https://github.com/vllm-project/vllm/issues/54360)
