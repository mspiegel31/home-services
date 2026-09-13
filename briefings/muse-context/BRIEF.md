# Brief: Muse context extension


## Question
Is 256K context usable or merely loadable?

## Supporting questions
1. What context limits, extension settings, and request path exist today for the local Muse profile?
2. What current primary-source evidence and reproducible local observations show whether a request beyond native context is accepted and remains useful?
3. Which source claims, version assumptions, and historical observations conflict or may have aged, and which conclusions remain unverified?
4. What quality, latency, memory, and operational tradeoffs determine whether extended context is worth relying on?
5. Which next read-only check would most change the decision to rely on or reject extended context?

## Decision this feeds
Whether to rely on extended context and what evidence must gate that choice.

## Audience
self

## Prior knowledge (do not re-explain)
Docker and Portainer operations, Git, APIs, and basic inference concepts, including context windows and model serving.

## Type
technology

## Diátaxis mode
guide

## Depth
10 minutes maximum; stop when the decision is supported, without padding.

## Source constraints
- Keep the scope to the homelab.
- Revalidate every falsifiable claim against current primary sources before drafting.
- Treat the supplied consolidation source as a lead and deletion-coverage scope, not automatically current truth.
- Separate configured state, historically observed behavior, proposed changes, and unverified assertions.
- Use read-only examples. Do not mutate deployments or accounts.
- Do not fetch sources or draft the briefing body until this contract is approved.

## Worked example
A read-only reconstruction of the local Muse profile receiving a request beyond the model's native context. Show the exact configured request path available from local evidence, name the context-extension mechanism at each step, and separate the observed boundary from the unverified boundary. Change one context-limit parameter and state what the resulting observation would establish. Do not deploy or mutate configuration.

## Interaction
None. Use static diagrams and tables only; provide no interactive controls.

## Consolidation sources
Deletion-coverage scope only:
- `research/muse-glimmer-nvidia-nvfp4-256k-vllm.md`

## Status
reviewed

## History
- 2026-09-09: brief written and approved
- 2026-09-09: primary evidence revalidated and draft completed
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
