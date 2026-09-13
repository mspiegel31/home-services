# Brief: Larger models and memory expansion

<!-- Every field below is settled in the gate interview before research or drafting. `check` fails on empty or TODO fields. -->

## Question
Which model or hardware upgrade offers a worthwhile improvement?

## Supporting questions
<!-- 3–6 questions the reader expects answered on the way to the primary one. Each becomes a body section. -->
1. Which model, serving path, memory limits, and Qwen quality baseline exist today on the current 72GB GPU system?
2. What current primary-source evidence and reproducible local observations support the modeled capacity and expected quality of each upgrade path?
3. Which source claims, software or hardware assumptions, and historical observations conflict or may have aged, and which conclusions remain unverified?
4. What tradeoffs in model quality, usable capacity, data movement, software support, cost, and operational complexity separate a larger-model/offload experiment, a system-RAM upgrade, and a DGX Spark purchase?
5. Which next read-only check or bounded experiment would most change the choice among keeping the current Qwen setup, testing a larger model, or buying hardware?

## Decision this feeds
Whether to run a larger-model or offload experiment instead of buying more system RAM or a DGX Spark, compared with the quality of the existing Qwen setup.

## Audience
self

## Prior knowledge (do not re-explain)
Docker and Portainer operations, Git, APIs, and basic inference concepts, including model serving, quantization, and memory capacity.

## Type
technology

## Diátaxis mode
guide

## Depth
10 minutes maximum; stop when the decision is supported, without padding.

## Source constraints
- Keep the scope to the homelab.
- Revalidate every falsifiable claim against current primary sources before drafting.
- Treat the supplied consolidation sources as leads and deletion-coverage scope, not automatically current truth.
- Separate configured state, historically observed behavior, proposed changes, modeled capacity, and unverified assertions.
- Use read-only examples. Do not mutate deployments or accounts.
- Do not invent throughput. Include it only when a cited measurement or a future bounded experiment supplies it.
- Do not fetch sources or draft the briefing body until this contract is approved.

## Worked example
A read-only, modeled comparison that starts with the current 72GB GPU system attempting a larger model. Show the capacity and allocation assumptions, then compare a system-RAM upgrade with a heterogeneous-host option that includes DGX Spark. Label every capacity figure as configured, historically observed, proposed, modeled, or unverified. Change one memory or offload parameter and identify the observation that would affect the decision. Do not invent throughput or mutate deployments or accounts.

## Interaction
None. Use static diagrams and tables only; provide no interactive controls.

## Consolidation sources
Deletion-coverage scope only:
- `research/oss-sota-moe-ram-offload-vs-qwen38-27b.md`
- `research/dgx-spark-rtx5000-heterogeneous-vllm-sglang.md`

## Status
reviewed

## History
- 2026-09-09: brief written
- 2026-09-09: approved contract retained; primary evidence revalidated and draft briefing completed
- 2026-09-09: restored independent and same-harness comparisons, separately labeled GLM evidence, deferred-family coverage, compact-quant caveats, and replacement acceptance criteria
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed, including the executed capacity table. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
