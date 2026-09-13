# Brief: Inference control plane and reasoning

## Question

How should model catalogs, thinking controls, and clients stay synchronized?

## Supporting questions

1. What model catalogs, aliases, and thinking controls are currently configured across clients, LiteLLM, llama-swap, and the inference backends?
2. What repository evidence and revalidated primary sources support the current request path and each claimed model capability?
3. Where do catalogs or thinking controls conflict, and which evidence is historically observed, aged, proposed, or still unverified?
4. What tradeoffs determine where catalog authority and capability negotiation should live?
5. Which read-only check would most change the synchronization and capability-contract decision?

## Decision this feeds

Choose the authoritative catalog and the synchronization and capability contract, while distinguishing implemented behavior from proposed work.

## Audience

self

## Prior knowledge (do not re-explain)

Docker and Portainer, Git, APIs, and basic inference concepts.

## Type

architecture

## Diátaxis mode

guide

## Depth

Target ten minutes or less. Condense prose and tables without dropping any approved supporting question or source topic. Do not pad.

## Source constraints

Treat the supplied repository documents as leads, not automatically current truth. Revalidate falsifiable claims against current primary sources and current repository evidence. Label configured state, historically observed behavior, proposed work, and unverified claims separately. Keep all examples read-only; do not deploy services or mutate accounts, infrastructure, or configuration.

## Worked example

Trace one concrete Oh My Pi client reasoning request through LiteLLM and llama-swap to the selected backend. Contrast it with the same path when the requested thinking level is unsupported or the selected model lacks reasoning capability. Show the full request path, control ownership, capability checks, and observed result using read-only evidence.

## Interaction

Static request-path diagrams and static tables only. No interactive controls.

## Consolidation sources

- `research/inference-control-plane-sync.md`
- `research/gateway-thinking-levels.md`
- `research/omp-litellm-reasoning-discovery.md`

These paths define deletion-coverage scope only. They remain source leads until revalidated. Main may delete them only after replacement coverage, rendering, and visual review pass.

## Status

reviewed

## History

- 2026-09-09: Brief approved.
- 2026-09-09: Primary evidence revalidated and draft completed; status remains draft pending Main review.
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
