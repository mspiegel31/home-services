# Brief: Architecture whiteboarding with LLMs

<!-- Every field below is settled in the gate interview before research or drafting. `check` fails on empty or TODO fields. -->

## Question
Which tool supports an effective human–LLM review loop?

## Supporting questions
1. What architecture-board and Mermaid workflows are available for a homelab human–LLM review loop, and which inspect, edit, and comment steps does each expose?
2. What primary-source and reproducible evidence supports each capability required by that loop?
3. Which claims in the consolidation source conflict with, or have aged relative to, current documentation, releases, or observed behavior?
4. Which tradeoffs between an architecture-board trial and a Mermaid workflow matter for review fidelity, edit ownership, feedback speed, privacy, and operating burden?
5. What smallest read-only trial or source check would change the selection?

## Decision this feeds
Select an architecture-board trial or retain a Mermaid workflow, based on verified inspect, edit, and comment capabilities.

## Audience
self

## Prior knowledge (do not re-explain)
Docker and Portainer, Git, APIs, and basic inference concepts.

## Type
tool

## Diátaxis mode
guide

## Depth
10 minutes maximum; stop as soon as the question is answered.

## Source constraints
- Limit the scope to the homelab case.
- Revalidate every decision-relevant claim against fetched primary sources before drafting. Treat supplied material as a lead that requires current verification.
- Distinguish locally configured facts, historically observed behavior, proposed designs, and unverified claims.
- Keep every example read-only. Do not change deployments or external accounts, create paid resources, or fabricate execution.

## Consolidation sources
- `research/ai-native-architecture-diagramming-tools.md`

This path defines consolidation and later deletion coverage only.

## Worked example
Trace one real homelab architecture-board review from actual documented input through human and LLM inspection, edits, and comments to the complete output, then compare the same case with Mermaid. Show the full documented inputs and outputs without elision. If a live run is unavailable, state that boundary and include only what the sources support. Do not modify an external account, create a paid resource, or claim an execution that did not occur.

## Interaction
Static diagrams and tables only; no interactive controls.

## Status
reviewed

## History
- 2026-09-09: brief written
- 2026-09-09: approved contract used for primary-source revalidation and draft synthesis
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`.
