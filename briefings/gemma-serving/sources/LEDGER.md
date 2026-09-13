# Source ledger

Every row records a source fetched on 2026-09-09. The `key` matches `references.bib`.

| key | url | fetched | summary |
|---|---|---|---|
| localgemma2026 | [sources/evidence.json](evidence.json) | 2026-09-09 | Repository revision, consolidation coverage, and read-only excerpts from the current serving configuration and image files. |
| google31bcard | <https://huggingface.co/google/gemma-4-31B-it> | 2026-09-09 | Google model card for Gemma 4 31B, including modalities, context, thinking, tool use, and limitations. |
| google31bconfig | <https://huggingface.co/google/gemma-4-31B-it/raw/main/config.json> | 2026-09-09 | Target architecture, 262144-token position limit, vocabulary, attention geometry, and final-logit soft cap. |
| googleassistantcard | <https://huggingface.co/google/gemma-4-31B-it-assistant> | 2026-09-09 | Google MTP assistant card and target-verification description. |
| googleassistantconfig | <https://huggingface.co/google/gemma-4-31B-it-assistant/raw/main/config.json> | 2026-09-09 | Assistant architecture, four BF16 layers, shared-KV metadata, backbone geometry, vocabulary, and 262144-token position limit. |
| unsloth31bcard | <https://huggingface.co/unsloth/gemma-4-31B-it-NVFP4> | 2026-09-09 | Exact configured target's vLLM requirement and NVFP4 serving guidance. |
| unsloth31bconfig | <https://huggingface.co/unsloth/gemma-4-31B-it-NVFP4/raw/main/config.json> | 2026-09-09 | Exact target's mixed NVFP4/FP8 compressed-tensors layout, FP8 KV scheme, architecture, and context limit. |
| zlabdflashcard | <https://huggingface.co/z-lab/gemma-4-31B-it-DFlash> | 2026-09-09 | DFlash drafter card, required open vLLM PR, launch shape, B300 measurements, and 15-token vLLM setting. |
| zlabdflashconfig | <https://huggingface.co/z-lab/gemma-4-31B-it-DFlash/raw/main/config.json> | 2026-09-09 | Five-layer mixed-attention BF16 drafter geometry, six target layers, block size 16, soft cap, and 262144-token limit. |
| nvidia31bcard | <https://huggingface.co/nvidia/Gemma-4-31B-IT-NVFP4> | 2026-09-09 | NVIDIA's separate NVFP4 export, vLLM integration, H100 evaluation, and target-only quality deltas. |
| vllmgemmarecipe | <https://recipes.vllm.ai/Google/gemma-4-31B-it?variant=nvfp4&hardware=b200> | 2026-09-09 | Current Gemma recipe, parser/cache/context guidance, and a stale nightly-only MTP note that conflicts with tagged v0.28.0 source. |
| vllmpr41703 | <https://github.com/vllm-project/vllm/pull/41703> | 2026-09-09 | Open, stale, needs-rebase Gemma DFlash PR and its current five-part correctness/compatibility fix set. |
| vllmpr41745 | <https://github.com/vllm-project/vllm/pull/41745> | 2026-09-09 | Merged Gemma 4 MTP implementation and external B300 NVFP4 K=7 measurement. |
| vllmpr49797 | <https://github.com/vllm-project/vllm/pull/49797> | 2026-09-09 | Merged heterogeneous Gemma 4 attention-configuration compatibility fix. |
| vllm028mtpmodel | <https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/model_executor/models/gemma4_mtp.py> | 2026-09-09 | Tagged stock implementation of the Gemma 4 MTP assistant, shared KV, normalization, and logits processing. |
| vllm028dflashmodel | <https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/model_executor/models/qwen3_dflash.py> | 2026-09-09 | Tagged generic DFlash loader with mixed-attention support but without the open Gemma-specific fixes. |
| vllm028specconfig | <https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/config/speculative.py> | 2026-09-09 | Tagged speculative-method detection and Gemma 4 MTP configuration path. |
| vllm028registry | <https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/model_executor/models/registry.py> | 2026-09-09 | Tagged native model registry for Gemma 4 target and assistant architectures. |
| vllmmainmtpmodel | <https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/models/gemma4_mtp.py> | 2026-09-09 | Current main-branch Gemma 4 MTP implementation. |
| vllmmaindflashmodel | <https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/models/qwen3_dflash.py> | 2026-09-09 | Current main-branch generic DFlash implementation, still lacking PR #41703's Gemma-specific path. |
| vllm028specdocs | <https://github.com/vllm-project/vllm/blob/v0.28.0/docs/features/speculative_decoding/README.md> | 2026-09-09 | Tagged speculative-decoding contract, losslessness qualifications, schema, and measurement caveats. |
| vllm028mtpdocs | <https://github.com/vllm-project/vllm/blob/v0.28.0/docs/features/speculative_decoding/mtp.md> | 2026-09-09 | Tagged Gemma assistant MTP guidance and supported assistant families. |
| vllm028memorydocs | <https://github.com/vllm-project/vllm/blob/v0.28.0/docs/configuration/conserving_memory.md> | 2026-09-09 | Tagged explanation of weight quantization, context, batch, multimodal profiling, and CUDA-graph memory controls. |
