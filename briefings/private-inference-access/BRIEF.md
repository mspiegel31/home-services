# Brief: Private inference access

<!-- Every field below is settled in the gate interview before research or drafting. `check` fails on empty or TODO fields. -->

## Question
Which access architecture satisfies the privacy requirements?

## Supporting questions
1. What exact locally configured or explicitly proposed request path carries a homelab client request through ingress to LiteLLM?
2. What local evidence and current primary sources support the claimed TLS, authentication, routing, logging, and data-exposure behavior at each hop?
3. Which statements in the consolidation source conflict with, or have aged relative to, current configuration, vendor documentation, or observed behavior?
4. Which tunnel and proxy trust-boundary tradeoffs matter for privacy, credential handling, TLS termination, failure modes, and operating burden?
5. What next read-only configuration or source check would resolve a prerequisite or change the architecture assessment?

## Decision this feeds
Assess the selected tunnel and proxy trust boundaries and identify any unresolved prerequisites before choosing the private inference access architecture.

## Audience
self

## Prior knowledge (do not re-explain)
Docker and Portainer, Git, APIs, and basic inference concepts.

## Type
architecture

## Diátaxis mode
guide

## Depth
10 minutes maximum; stop as soon as the question is answered.

## Source constraints
- Limit the scope to the homelab case.
- Revalidate every decision-relevant claim against fetched primary sources before drafting. Treat supplied material as a lead that requires current verification.
- Distinguish locally configured facts, historically observed behavior, proposed designs, and unverified claims.
- Keep every example and check read-only. Do not change services, deployments, or external accounts, and do not create paid resources or fabricate execution.

## Consolidation sources
- `litellm-tunnel-privacy-plan.md`

This path defines consolidation and later deletion coverage only.

## Worked example
Trace one client request through the exact locally configured or explicitly proposed ingress to LiteLLM. At each hop, show the input, output, authentication decision, TLS state, termination point, and trust boundary. Contrast the same request after TLS termination moves one hop, including any resulting credential exposure or trust-boundary change. Use only documented configuration and read-only evidence; label any unverified segment rather than inventing it.

## Interaction
Static request-path diagrams and tables only; no interactive controls.

## Status
reviewed

## History
- 2026-09-09: brief written
- 2026-09-09: approved question map researched and drafted; status remains draft pending integration review.
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
