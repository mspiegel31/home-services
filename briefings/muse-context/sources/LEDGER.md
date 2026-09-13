# Source ledger

One row per source used. `key` matches the BibTeX key in `references.bib`.

| key | url | fetched | summary |
|-----|-----|---------|---------|
| nvidiaMuseNvfp4 | https://huggingface.co/nvidia/Muse-Glimmer-30B-NVFP4 | 2026-09-09 | NVIDIA's current artifact card: supported context, mixed-precision quantization, tested vLLM 0.28.0 launch, calibration, and evaluation policy. Fetched through `hf models card` and the Hugging Face reader. |
| metaMuseCard | https://huggingface.co/meta-models/Muse-Glimmer-30B | 2026-09-09 | Meta's current model architecture, 131,072+ context statement, attention pattern, sliding window, and local-layer RoPE. |
| metaMusePrompting | https://ai.developer.meta.com/docs/muse-glimmer/prompting | 2026-09-09 | Meta's current prompting and chat-template guidance, including its unnumbered longer-context statement. |
| peng2026yarn | https://arxiv.org/abs/2309.00071 | 2026-09-09 | Primary YaRN paper; the current arXiv v3 and official BibTeX date the revision to 2026 and describe RoPE context extension. |
| vllmModelConfig028 | https://github.com/vllm-project/vllm/blob/v0.28.0/vllm/config/model.py | 2026-09-09 | Pinned vLLM source showing recursive nested Hugging Face overrides, text-config selection, and maximum-length validation order. Fetched with the GitHub file API. |
| vllmMuseRecipe | https://recipes.vllm.ai/meta-models/Muse-Glimmer-30B | 2026-09-09 | vLLM's Muse recipe and its explicitly rope-extended RTX 5090 memory observations. |
| localMuseEvidence | sources/evidence.json | 2026-09-09 | Repository-local provenance for the configured LiteLLM, llama-swap, Docker, and vLLM request path at revision `a4a45cbe68c4eaef67f45bf8807605475fb23efa`. |
