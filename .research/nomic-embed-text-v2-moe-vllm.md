# Nomic Embed Text v2 MoE on the home inference host

## Decision

Run `nomic-ai/nomic-embed-text-v2-moe` as a CPU-only Hugging Face Text Embeddings Inference (TEI) service in the LiteLLM stack. Route it directly through LiteLLM. Keep it outside llama-swap and the GPU vLLM pool.

TEI explicitly lists this checkpoint as supported and exposes an OpenAI-compatible embeddings endpoint. vLLM can serve pooling models, and current releases provide x86 CPU images, but the inference host has AVX2 rather than the recommended AVX-512. The Nomic checkpoint also declares custom model code. Its model card requires `trust_remote_code=True`, which violates this repository's vLLM backend policy. TEI loads the model through its native NomicBERT Candle implementation without executing repository Python.

Sources:

- [Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)
- [TEI supported models and CPU image](https://github.com/huggingface/text-embeddings-inference#supported-models)
- [vLLM pooling models](https://docs.vllm.ai/en/stable/models/pooling_models/)
- [vLLM CPU requirements](https://docs.vllm.ai/en/stable/getting_started/installation/cpu/)

## Model contract

The checkpoint contains 475,292,928 FP32 parameters. Nomic describes 475M total parameters, 305M active parameters per inference, eight experts, and top-2 routing. All expert weights remain resident; the active parameter count reduces computation, not weight storage.

The service contract is:

- Maximum input: 512 tokens.
- Default output: 768 normalized dimensions.
- Matryoshka output: dimensions may be truncated to 256 before normalization.
- Pooling: mean over non-padding tokens, followed by L2 normalization.
- Retrieval prefixes: `search_query: ` for queries and `search_document: ` for documents.

The service cannot infer whether arbitrary input is a query or a document. Callers must supply the correct prefix. Changing an existing application's embedding model requires a complete re-index because vectors from the old and new models are not interchangeable.

Sources:

- [Nomic model card usage and architecture](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)
- [Checkpoint configuration](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe/raw/main/config.json)
- [Sentence Transformers pooling configuration](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe/raw/main/1_Pooling/config.json)
- [Sentence Transformers prompt configuration](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe/raw/main/config_sentence_transformers.json)

## Memory footprint

The theoretical FP32 weight floor is:

`475,292,928 parameters × 4 bytes = 1,901,171,712 bytes = 1.771 GiB`

The deployed container measured:

- Docker working-set memory: **3.089–4.041 GiB**, depending on active file-cache state.
- Anonymous memory: **2.772 GiB**.
- File cache: **1.53–1.811 GiB**, mostly the 1.9 GB safetensors checkpoint and reclaimable under pressure.
- Total cgroup-charged anonymous + file + kernel memory: **4.32–4.60 GiB**.
- Settled idle CPU: **0.28–0.48%**.

Budget **2.8 GiB of anonymous memory** and **4.6 GiB total** while the checkpoint remains cached. The host had 37 GiB available after consolidation, so this service has ample headroom.

These are live measurements from the `ai` host on 2026-09-18, not estimates. The deployed service uses four tokenizer workers. An initial smoke run with TEI's auto-selected 13 workers measured 5.155 GiB of Docker working-set memory, but different cache and runtime state prevent assigning the full difference to worker count.

## Measured behavior

The deployed path is:

`OpenAI client -> LiteLLM :4000 -> TEI over the shared litellm Docker network -> CPU`

Observed through LiteLLM:

- One 768-dimensional embedding: HTTP 200 in 137.8 ms.
- Two 256-dimensional embeddings: HTTP 200 in 232.2 ms.
- Correct model id and token usage returned by `/v1/embeddings`.
- No Docker GPU device request; runtime is standard `runc`.
- llama-swap remained healthy and unchanged.

TEI selected its native Candle `NomicBert` CPU backend. It first probes for optional ONNX artifacts, logs their absence, then falls back to Candle. The ONNX probe errors are expected for this checkpoint and do not make the service unhealthy.

## Deployment configuration

The service lives in `services/litellm/docker-compose.yml`. It:

- pins TEI `cpu-1.9` by the linux/amd64 image digest;
- mounts the existing `/mnt/models/huggingface` cache;
- shares the stack's internal `litellm` network without publishing a LAN port;
- runs FP32, four tokenizer workers, four batch requests, and 2,048 batch tokens;
- uses `restart: unless-stopped`, so the model stays resident independently of llama-swap TTL and matrix routing.

LiteLLM advertises `nomic-embed-text-v2-moe` as an embedding model with a 512-token input limit and forwards `dimensions` and `encoding_format` to TEI.

## vLLM alternative

Current vLLM exposes pooling models through `/v1/embeddings` and supports `--runner pooling`. Its CPU documentation publishes `vllm/vllm-openai-cpu:latest-x86_64`, but describes AVX2 as limited-feature support. A candidate invocation would be:

```bash
docker run --rm -p 8000:8000 \
  vllm/vllm-openai-cpu:latest-x86_64 \
  --model nomic-ai/nomic-embed-text-v2-moe \
  --runner pooling \
  --dtype float32 \
  --max-model-len 512 \
  --trust-remote-code \
  --served-model-name nomic-embed-text-v2-moe
```

This invocation is intentionally **not deployed or verified**. It executes model repository code, conflicts with the repository's no-remote-code rule, and uses vLLM's limited AVX2 CPU path. TEI has explicit native support for this exact model and is the lower-risk resident service.

Sources:

- [vLLM OpenAI embeddings example](https://docs.vllm.ai/en/stable/examples/pooling/embed/)
- [vLLM CPU installation and images](https://docs.vllm.ai/en/stable/getting_started/installation/cpu/)
- [llama-swap TTL and preload configuration](https://github.com/mostlygeek/llama-swap/blob/main/docs/config.example.yaml)
