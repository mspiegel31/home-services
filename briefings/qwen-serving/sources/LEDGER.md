# Source ledger

| key | URL | Fetched | Summary |
|---|---|---|---|
| qwen-bf16-card | https://huggingface.co/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 | 2026-09-09 | Pinned Qwen BF16 model card; architecture, context, reasoning, serving, and benchmark claims. |
| qwen-fp8-card | https://huggingface.co/Qwen/Qwen3.8-27B-FP8/tree/017b9c7af6b5689d5dd426a76e0bc077eb5ca20a | 2026-09-09 | Pinned Qwen FP8 model card; blockwise FP8 recipe and Qwen's near-identical-metrics claim. |
| radixark-bf16-lmhead-card | https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead/tree/009632fef96dd349150baa780c984e62e70e91fe | 2026-09-09 | Pinned mixed NVFP4 target card; BF16 embedding/language-model head distinction and third-party evaluations. |
| unsloth-nvfp4-card | https://huggingface.co/unsloth/Qwen3.8-27B-NVFP4/tree/f0b7c9e722f5565102fff8481c99e4d86ae099c7 | 2026-09-09 | Pinned Unsloth mixed NVFP4 model card and serving guidance. |
| dflash2-card | https://huggingface.co/incoai/Qwen3.8-27B-DFlash2/tree/dedf8df68adfb1afeaf7b7480c0a0243108177b4 | 2026-09-09 | Pinned DFlash2 draft-model card; block geometry, vLLM/SGLang configuration, and H200 measurements. |
| ninfer-card | https://huggingface.co/neroued/Qwen3.8-27B-nvfp4-NInfer/tree/11dbbbbbc33db198afe2f020c9232c771ff7031be | 2026-09-09 | Pinned NInfer artifact card; engine-specific format, profile composition, and acceptance evidence. |
| sglang-qwen-cookbook | https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/Qwen/Qwen3.8-27B.mdx | 2026-09-09 | Current SGLang Qwen3.8 cookbook; platform recipes, DFlash2/MTP setup, state-memory sizing, parser contract, and validation scope. |
| vllm-qwen-recipe | https://recipes.vllm.ai/Qwen/Qwen3.8-27B | 2026-09-09 | Current vLLM Qwen3.8 recipe; supported checkpoints and serving profile. |
| vllm-tool-calling | https://github.com/vllm-project/vllm/blob/v0.28.0/docs/features/tool_calling.md | 2026-09-09 | Tagged vLLM tool-calling contract; parser, chat-template, automatic selection, and schema-constrained behavior. |
| vllm-prefix-cache | https://github.com/vllm-project/vllm/blob/v0.28.0/docs/design/prefix_caching.md | 2026-09-09 | Tagged vLLM automatic-prefix-cache design; block hashing, reuse, references, and eviction. |
| vllm-issue-53726 | https://github.com/vllm-project/vllm/issues/53726 | 2026-09-09 | Open SM120 hybrid-GDN/native-MTP illegal-memory-access report and follow-up status. |
| vllm-issue-54360 | https://github.com/vllm-project/vllm/issues/54360 | 2026-09-09 | Open hybrid-model prefix-cache regression report under MTP and DFlash speculation. |
| vllm-issue-52540 | https://github.com/vllm-project/vllm/issues/52540 | 2026-09-09 | Open SM120 mixed-precision FP8 scaled-matrix-multiplication failure report and kernel workaround. |
| vllm-issue-54623 | https://github.com/vllm-project/vllm/issues/54623 | 2026-09-09 | Open Qwen3.5-family loader report for dropped checkpoint FP8 KV-cache scales, including the exact Unsloth Qwen3.8 checkpoint. |
| vllm-pr-54624 | https://github.com/vllm-project/vllm/pull/54624 | 2026-09-09 | Open proposed fix that remaps checkpoint KV-cache scale names before loading Qwen3.5-family weights. |
| dgx-fp8-nvfp4 | https://forums.developer.nvidia.com/t/qwen3-8-27b-on-dgx-spark-using-vllm-nvfp4-vs-fp8-performance/380258 | 2026-09-09 | Community DGX Spark matched-flag FP8 versus Unsloth NVFP4 throughput and latency measurements. |
| dgx-decoder-tool | https://forums.developer.nvidia.com/t/qwen3-8-27b-benchmarking-on-one-dgx-spark-dflash2-beat-vllm-mtp-and-greedy-beat-the-thinking-sampler/380957 | 2026-09-09 | Community DGX Spark cross-engine decoder, sampler, tool-call, and follow-up checkpoint measurements; not a clean engine-only comparison. |
| opencode-skills | https://opencode.ai/docs/skills/ | 2026-09-09 | Current OpenCode skill discovery and on-demand loading behavior. |
| rtx6kpro-common-issues | https://github.com/local-inference-lab/rtx6kpro/blob/master/troubleshooting/common-issues.md | 2026-09-09 | Current community Blackwell failure catalogue; JIT-cache invalidation and speculative-decoding hazards. |
| local-serving-config | sources/evidence.json | 2026-09-09 | SHA-bound excerpts from current llama-swap Qwen profiles and shared vLLM arguments. |
| local-litellm-routing | sources/evidence.json | 2026-09-09 | SHA-bound excerpts from current LiteLLM Qwen model registration and advertised reasoning tiers. |
| local-callback-policy | sources/evidence.json | 2026-09-09 | SHA-bound excerpt from the current LiteLLM reasoning-control transformation. |
| local-historical-observations | sources/evidence.json | 2026-09-09 | Dated observations preserved from source notes; explicitly not rerun for this briefing. |
| local-audit-evidence | sources/evidence.json | 2026-09-09 | Preserved tool-calling audit corrections, rejected percentages, and non-Qwen comparison shortlist. |
