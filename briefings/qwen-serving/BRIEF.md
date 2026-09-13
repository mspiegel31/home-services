# Brief: Qwen quality, speculation, and tool calling

<!-- Every field below is settled in the gate interview before research or drafting. `check` fails on empty or TODO fields. -->

## Question
Which precision, decoder, and serving profile should be the daily driver?

## Supporting questions
1. Which Qwen model, precision, decoder, cache, speculation, and serving configurations are configured locally, historically observed, proposed, or still unverified?
2. What primary-source and local evidence supports each profile's quality, throughput, context capacity, and tool-calling behavior?
3. Which findings conflict, depend on a different model, runtime, or GPU, or may have aged past the versions now in scope?
4. What quality, throughput, context-length, tool-calling, portability, and operational tradeoffs matter when choosing the daily driver?
5. Which controlled, comparable local evaluation would most change the choice?

## Decision this feeds
Choose the Qwen quality and throughput profile to run as the daily driver, then choose the next comparable evaluation needed to confirm or revise that choice.

## Audience
self

## Prior knowledge (do not re-explain)
Docker and Portainer operation, Git workflows, API requests, and basic local-model inference concepts.

## Type
technology

## Diátaxis mode
guide

## Depth
10 minutes maximum; condense prose and tables without dropping any approved supporting question or source topic; do not pad.

## Source constraints
Use the listed consolidation sources as leads and revalidate every falsifiable claim against current primary sources for the exact model, runtime, decoder, and hardware version in scope. Keep configured state, historically observed results, proposed settings, and unverified claims distinct. Use read-only inspection and examples only; do not change deployments, services, Portainer state, or accounts. Never invent benchmark results, model output, or configuration details.

## Worked example
Reconstruct an exact local Qwen launch configuration and stress it with a long-context, tool-calling request. Trace the request through the serving and decoding mechanisms to the observable outcome. Compare one precision or speculation condition changed in isolation, using actual local evidence and current primary sources; label any missing outcome unverified rather than inventing it.

## Interaction
Static diagrams and tables only; no interactive controls.

## Consolidation sources
- `research/qwen3-8b-bf16-fp8-nvfp4-quality.md`
- `research/qwen3-8-unsloth-nvfp4-vs-fp8-daily-drive.md`
- `research/qwen38-27b-nvfp4-fp8-bf16-vllm-performance.md`
- `research/vllm-qwen38-dflash-prefix-cache-tuning.md`
- `research/ninfer-mtp-portability-vllm-sglang.md`
- `research/rtx5000-72gb-lessons-from-rtx6kpro.md`
- `research/local-agent-model-tool-calling-sanity-check.md`

## Status
reviewed

## History
- 2026-09-09: interview contract approved; evidence-backed draft prepared for integration review.
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
