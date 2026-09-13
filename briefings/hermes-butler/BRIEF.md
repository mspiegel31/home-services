# Brief: Hermes Butler architecture and readiness

<!-- Every field below is settled in the gate interview before research or drafting. `check` fails on empty or TODO fields. -->

## Question
What is implemented versus still planned?

## Supporting questions
<!-- 3–6 questions the reader expects answered on the way to the primary one. Each becomes a body section. -->
1. Which Butler, Hermes, gateway, model-endpoint, meal, and grocery components are implemented or configured in the current repository?
2. What current repository evidence supports each readiness claim along the Signal request path?
3. Where does the setup plan conflict with current evidence, appear aged, describe only proposed work, or leave a claim unverified?
4. What tradeoffs and remaining prerequisites determine whether Butler is ready for use without a deployment?
5. Which read-only check would most change the readiness decision?

## Decision this feeds
Understand Butler readiness and its remaining prerequisites without deploying it.

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
Use current repository evidence to distinguish implemented or configured state from historically observed behavior, proposed work, and unverified claims. Treat the supplied setup plan as a lead, not proof that its steps were implemented. After approval, revalidate falsifiable claims against current primary sources where applicable. Do not perform external fetches or corpus research before approval. Keep all examples read-only; do not deploy services or mutate accounts, infrastructure, or configuration.

## Worked example
Trace one concrete Signal message through the gateway, Hermes, the model endpoint, and the meal or grocery integration where current repository evidence shows that integration exists. Contrast it with a denied sender or unavailable dependency. Show the full request path and observed boundaries without assuming the setup plan was implemented.

## Interaction
STATIC request-path diagrams and static tables only. No interactive controls.

## Consolidation sources
- `research/hermes-butler-setup-plan.md`

This path defines deletion-coverage scope only. It remains a source lead until revalidated. Delete the superseded source document only after Main verifies complete replacement coverage and rendering, not during this contract stage. `.slim/deepwork` execution records remain untouched and are not deletion targets.

## Status
reviewed

## History
- 2026-09-09: brief written
- 2026-09-09: user approved the contract and research began; draft remains unreviewed pending Main's audit, render, and visual inspection
- 2026-09-09: citation audit, render, source-coverage review, and browser/print verification passed. Listed consolidation sources were removed; their hashes and evidence remain in `sources/evidence.json`. Execution records remain untouched.
