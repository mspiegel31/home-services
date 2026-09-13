# Source ledger

One row per URL actually fetched. The key column matches the BibTeX key in `references.bib`. Local observations point to the preserved evidence bundle.

| key | url | fetched | summary |
|-----|-----|---------|---------|
| local-stack-20260909 | `sources/evidence.json` | 2026-09-09 | Repository configuration for the llama-swap, vLLM, SGLang, and LiteLLM Qwen serving path at revision `a4a45cbe`. |
| local-host-20260909 | `sources/evidence.json` | 2026-09-09 | Read-only `free`, `nvidia-smi`, and Hugging Face cache observations, including dated capacity and cache consistency output. |
| qwen-flash-card | https://huggingface.co/Qwen/Qwen3.8-Flash-Next | 2026-09-09 | Official architecture, license, context, tensor metadata, same-table Qwen and DeepSeek benchmark comparison, and evaluation settings for Qwen3.8-Flash-Next. |
| qwen-27b-fp8-card | https://huggingface.co/Qwen/Qwen3.8-27B-FP8 | 2026-09-09 | Official Qwen3.8-27B-FP8 identity, Apache-2.0 license, context, and quality-baseline claims. |
| qwen-flash-nvfp4-card | https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4 | 2026-09-09 | NVIDIA derivative license, quantization, tensor payload, repository storage total, runtime notes, and model identity. |
| glm-flash-card | https://huggingface.co/zai-org/GLM-5.3-Flash | 2026-09-09 | Official GLM identity, MIT license, tensor payload, runtime support, reasoning-effort controls, and benchmark methodology notes. |
| deepseek-v4-card | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 | 2026-09-09 | Official DeepSeek identity, MIT license, tensor payload, runtime examples, and separately configured DeepSeek Harness benchmark evidence. |
| gpt-oss-report | https://arxiv.org/html/2508.10925 | 2026-09-09 | Primary model report for gpt-oss architecture, Apache-2.0 license, MXFP4 checkpoint size, and single-GPU fit claim. |
| nemotron-card | https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 | 2026-09-09 | NVIDIA license, architecture, NVFP4 tensor metadata, minimum hardware statement, and benchmark context. |
| mistral-small-card | https://huggingface.co/mistralai/Mistral-Small-4-119B-2603-NVFP4 | 2026-09-09 | Apache-2.0 model identity, architecture, context, and artifact storage metadata. |
| llama-server-readme | https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md | 2026-09-09 | Current llama.cpp server controls for mmap, memory locking, GPU layers, CPU MoE, tensor overrides, splits, fit targets, and KV offload. |
| llama-prefetch-pr | https://github.com/ggml-org/llama.cpp/issues/21067 | 2026-09-09 | Community implementation report with hardware-specific prefetch, latency, decode, and host-to-device measurements. |
| devquasar-heterogeneous | https://devquasar.com/ai/edge-ai/distributed-inference-cluster-dgx-spark-rtx-6000-pro/ | 2026-09-09 | Third-party mixed DGX Spark and RTX PRO 6000 experiment, retained only as topology-specific compatibility evidence. |
| vllm-parallelism | https://github.com/vllm-project/vllm/blob/main/docs/serving/parallelism_scaling.md | 2026-09-09 | Official vLLM tensor/pipeline parallelism, multi-node environment, Ray, and network guidance. |
| vllm-env | https://github.com/vllm-project/vllm/blob/main/vllm/envs.py | 2026-09-09 | Current source definition for manual pipeline layer partition configuration. |
| sglang-pipeline | https://docs.sglang.io/docs/advanced_features/pipeline_parallelism.md | 2026-09-09 | Official SGLang cross-node pipeline parallelism and custom uneven layer partition controls. |
| spark-hardware | https://docs.nvidia.com/dgx/dgx-spark/hardware.html | 2026-09-09 | Official DGX Spark unified-memory capacity, bandwidth, processor, networking, and stated model-size limits. |
| vllm-spark | https://vllm.ai/blog/2026-06-01-vllm-dgx-spark | 2026-09-09 | vLLM description of Spark's shared memory consumers and model-specific memory tuning. |
| spark-vllm-stacked | https://build.nvidia.com/spark/vllm/stacked-sparks | 2026-09-09 | NVIDIA's documented multi-node vLLM recipe for connected DGX Spark systems. |
| spark-sglang | https://build.nvidia.com/spark/sglang | 2026-09-09 | NVIDIA's validated single-Spark SGLang environment and model matrix. |
| pair-readme | https://github.com/NVIDIA/Personal-AI-Router/blob/main/README.md | 2026-09-09 | Official router boundary: independent requests go to one node; no model, memory, or in-flight request pooling; supported engine scope. |
| aa-methodology-v43 | https://artificialanalysis.ai/methodology/intelligence-benchmarking | 2026-09-09 | Current v4.3 index composition, category weighting, testing parameters, and versioned methodology. |
| aa-qwen-27b | https://artificialanalysis.ai/models/qwen3-8-27b | 2026-09-09 | Independent hosted-provider result for Qwen3.8-27B at xhigh under Intelligence Index v4.3. |
| aa-qwen-flash | https://artificialanalysis.ai/models/qwen3-8-flash-next | 2026-09-09 | Independent hosted-provider result for Qwen3.8-Flash-Next under Intelligence Index v4.3. |
| aa-glm53 | https://artificialanalysis.ai/models/glm-5-3-flash | 2026-09-09 | Independent hosted-provider result for GLM-5.3-Flash under Intelligence Index v4.3. |
| aa-deepseek-v4 | https://artificialanalysis.ai/models/deepseek-v4-flash | 2026-09-09 | Independent hosted-provider result for DeepSeek-V4-Flash-0731 at max effort under Intelligence Index v4.3. |
| glm-benchmark-figure | https://raw.githubusercontent.com/zai-org/GLM-5/refs/heads/main/resources/bench_53.png | 2026-09-09 | Official GLM-5.3-Flash figure with separately configured agent, tool, and GDPval-AA benchmark results. |
| historical-research-20260909 | `sources/evidence.json` | 2026-09-09 | Historical, unverified model-size, prior-index, exclusion, and acceptance-criteria claims preserved from the original local survey. |
