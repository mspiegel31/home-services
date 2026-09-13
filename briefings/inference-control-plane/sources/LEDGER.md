# Source ledger

Every row records a source fetched on 2026-09-09. `key` matches `references.bib`; local repository and workstation evidence is preserved in `sources/evidence.json` with secrets excluded.

| key | url | fetched | summary |
|---|---|---|---|
| localEvidence2026 | `sources/evidence.json` | 2026-09-09 | Hashes the three consolidation sources and preserves current repository, OMP-cache, and OpenCode excerpts. |
| ompLiteLLM2026 | https://github.com/can1357/oh-my-pi/blob/main/packages/catalog/src/provider-models/openai-compat.ts | 2026-09-09 | Current LiteLLM rich-endpoint discovery fields, API selection, reference enrichment, and capability mapping. |
| ompThinkingPolicy2026 | https://github.com/can1357/oh-my-pi/blob/main/packages/catalog/src/compat/resolve.ts | 2026-09-09 | Current explicit-thinking precedence and generic fallback effort ladders. |
| liteLLMHostedVLLM2026 | https://github.com/BerriAI/litellm/blob/litellm_internal_staging/litellm/llms/hosted_vllm/chat/transformation.py | 2026-09-09 | Current hosted-vLLM request parameter support and `thinking`-to-`reasoning_effort` transformation. |
| llamaSwapReadme2026 | https://github.com/mostlygeek/llama-swap/blob/main/README.md | 2026-09-09 | Model-ID routing, OpenAI endpoints, process swapping, Docker lifecycle, TTL, and matrix features. |
| llamaSwapSchema2026 | https://github.com/mostlygeek/llama-swap/blob/main/config-schema.json | 2026-09-09 | Current schema for models, capabilities, arbitrary metadata, lifecycle, filters, and routing. |
| openCodeModels2026 | https://opencode.ai/docs/models/ | 2026-09-09 | Current custom model configuration and per-model variant syntax. |
| openCodeProviders2026 | https://opencode.ai/docs/providers/ | 2026-09-09 | Current custom provider, base-URL, and model-list behavior. |
| aiSdkOpenAICompat2026 | https://github.com/vercel/ai/blob/5ec21a6946e13159d3c353c3fcd170ca8564d378/packages/openai-compatible/src/chat/openai-compatible-chat-language-model.ts | 2026-09-09 | Exact AI SDK serialization of `reasoningEffort` to `reasoning_effort`. |
| liteLLMModelManagement2026 | https://docs.litellm.ai/docs/proxy/model_management | 2026-09-09 | Config-owned and DB-owned model coexistence, settings overlays, and source-of-truth guidance. |
| hurlManual2026 | https://hurl.dev/docs/manual.html | 2026-09-09 | Declarative HTTP sequences, captures, assertions, and test-oriented execution. |
| vllmRouter2026 | https://github.com/vllm-project/router/blob/main/README.md | 2026-09-09 | Request forwarding, load balancing, service discovery, and prefill/decode routing scope. |
| localAIDistributed2026 | https://localai.io/docs/features/distributed-mode/ | 2026-09-09 | PostgreSQL/NATS control plane, dynamic backend installation, VRAM placement, and LRU eviction. |
| rayServeLLM2026 | https://docs.ray.io/en/latest/serve/llm/index.html | 2026-09-09 | Ray Serve LLM multi-node, multi-model deployment, autoscaling, and vLLM/SGLang support. |
| kserveDeploy2026 | https://kserve.github.io/website/docs/admin-guide/kubernetes-deployment | 2026-09-09 | KServe Standard/Knative modes and current Kubernetes installation requirements. |
| nineRouter2026 | https://github.com/decolua/9router/blob/main/README.md | 2026-09-09 | Coding-client provider routing, quota fallback, format translation, and token compression. |
| checkJsonschema2026 | https://github.com/python-jsonschema/check-jsonschema/blob/main/README.md | 2026-09-09 | JSON Schema CLI and pre-commit validation using local or remote schemas. |
| vllmReasoning028 | https://github.com/vllm-project/vllm/blob/v0.28.0/docs/features/reasoning_outputs.md | 2026-09-09 | Pinned vLLM reasoning parser, request controls, response shape, and request-level precedence. |
