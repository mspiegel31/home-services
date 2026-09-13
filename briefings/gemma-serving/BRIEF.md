# Brief: Gemma serving and tuning

<!-- Every field below is settled in the gate interview before research or drafting. `check` fails on empty or TODO fields. -->

## Question
What is supported, and what still needs measurement?

## Supporting questions
1. Which Gemma model, serving runtime, decoder, context, and speculation configurations are configured locally, historically observed, proposed, or still unverified?
2. What current primary-source and local evidence establishes support, compatibility, context capacity, and measured serving behavior?
3. Which findings conflict, rely on different versions or hardware, or may have aged past the Gemma and serving stack now in scope?
4. What safety, compatibility, quality, throughput, context-capacity, and operational tradeoffs matter when choosing a Gemma serving and speculation path?
5. Which controlled local measurement would most change the path or its tuning requirements?

## Decision this feeds
Choose a safe Gemma serving and speculation path, then define the tuning evidence required before treating it as the local default.

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
Use the listed consolidation source as a lead and revalidate every falsifiable claim against current primary sources for the exact Gemma model, serving runtime, decoder, and hardware version in scope. Keep configured state, historically observed results, proposed settings, and unverified claims distinct. Use read-only inspection and examples only; do not change deployments, services, Portainer state, or accounts. Never invent benchmark results, model output, support claims, or configuration details.

## Worked example
Reconstruct an exact local Gemma launch configuration and stress it at the point where context capacity or speculative-decoding compatibility becomes material. Trace the serving and decoding mechanisms to the observable outcome. Compare one context or speculation setting changed in isolation, using actual local evidence and current primary sources; label any missing outcome unverified rather than inventing it.

## Interaction
Static diagrams and tables only; no interactive controls.

## Consolidation sources
- `research/gemma4-31b-dflash-vllm-tuning.md`

## Status
reviewed

## History
- 2026-09-09: approved; evidence revalidated and draft completed
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
