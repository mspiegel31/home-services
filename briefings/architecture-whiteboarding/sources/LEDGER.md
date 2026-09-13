# Source ledger

One row per source used or fetched for revalidation. `key` matches the BibTeX key in `references.bib`.

| key | url | fetched | summary |
|-----|-----|---------|---------|
| miro-tools | https://developers.miro.com/docs/miro-mcp-tools | 2026-09-09 | Current Canvas Tool and comment-tool inventory; SVG reads and updates, stable `data-miro-id` values, supported object types, and deprecated tool families. |
| miro-limits | https://developers.miro.com/docs/mcp-usage-and-daily-limits | 2026-09-09 | Daily MCP call limits by plan, per-call counting, blocking behavior, and UTC reset time. |
| miro-faq | https://developers.miro.com/docs/miro-mcp-server-frequently-asked-questions | 2026-09-09 | MCP capability scope, OAuth and board permissions, enterprise controls, one-team connection behavior, and the distinction from Miro's full REST API. |
| miro-changelog | https://developers.miro.com/changelog/canvas-tools-replace-layout-tools | 2026-09-09 | Migration from `layout_*` to `canvas_*`, SVG patch behavior, narrow frame reads, and explicit deletion guidance. |
| miro-setup | https://developers.miro.com/docs/connecting-to-miro-mcp | 2026-09-09 | Remote MCP endpoint, client configuration shape, OAuth flow, and team-specific authorization. |
| miro-usecases | https://developers.miro.com/docs/mcp-use-cases-and-example-prompts | 2026-09-09 | First-party architecture, board-summary, and comment-handling prompt examples plus safety guidance. |
| miro-sidekicks | https://help.miro.com/hc/en-us/articles/30139627329042-Sidekicks | 2026-09-09 | In-board Sidekick context selection, plan availability, and custom-source limits. Not used for the decision because MCP exposes the required loop directly. |
| miro-pricing | https://miro.com/pricing/ | 2026-09-09 | Current Free, Starter, and Business plan descriptions and advertised MCP allowances. Decision uses the developer limits page for call quotas. |
| eraser-mcp | https://docs.eraser.io/mcp | 2026-09-09 | Remote and local server setup, OAuth or API-key access, diagram generation and edit, CRUD, search, export, privacy defaults, and credit use. |
| eraser-pricing | https://www.eraser.io/pricing | 2026-09-09 | Current file, AI-diagram, history, private-file, and monthly or annual plan limits. |
| eraser-security | https://docs.eraser.io/security | 2026-09-09 | Vendor security claims and enterprise self-host, private cloud, and single-tenancy options. |
| figma-guide | https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server | 2026-09-09 | Remote and desktop MCP availability, plan and seat access, native Figma and FigJam modification, supported clients, and permission boundaries. |
| figma-skills | https://help.figma.com/hc/en-us/articles/39166810751895-Figma-skills-for-MCP | 2026-09-09 | FigJam create and modify operations for shapes, connectors, sections, tables, and code blocks, plus beta seat limits. |
| figma-write | https://developers.figma.com/docs/figma-mcp-server/write-to-canvas/ | 2026-09-09 | Existing-file write requirements, Plugin API execution, incremental editing guidance, output limits, and beta cleanup warning. |
| figma-limits | https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/ | 2026-09-09 | Current read-tool rate limits by plan and seat and client-catalog restrictions. Not material to the first read-only trial. |
| lucid-mcp | https://help.lucid.co/hc/en-us/articles/42578801807508-Integrate-Lucid-with-AI-tools-using-the-Lucid-MCP-server | 2026-09-09 | Remote and read-only endpoints, create/edit/search/export/comment scope, plan availability, admin control, vendor data-retention statement, and static-diagram limitation. |
| whimsical-tools | https://whimsical.com/learn/ai/mcp-tools | 2026-09-09 | Current remote and desktop tool lists, object fetch and edit operations, layout, undo, and full comment lifecycle. |
| whimsical-mcp | https://whimsical.com/learn/integrations/mcp | 2026-09-09 | Remote endpoint and OAuth setup plus the separate desktop server's open-app and support-enablement requirements. |
| whimsical-pricing | https://whimsical.com/pricing | 2026-09-09 | Current board-object, document-block, history, and editor pricing limits. Not material to the first trial choice. |
| tldraw-agent | https://tldraw.dev/starter-kits/agent | 2026-09-09 | Agent Starter Kit setup, provider support, structured and visual context, actions, history, streaming, linting, and configurable critique modes. |
| tldraw-mcp | https://tldraw.dev/blog/tldraw-mcp-app | 2026-09-09 | MCP App launch, supported interactive-canvas flow, current create/edit/delete tools, and host rollout boundary. |
| tldraw-sync | https://tldraw.dev/docs/sync | 2026-09-09 | Prototype versus production sync guidance, WebSocket rooms, storage, and missing authentication, authorization, limits, snapshots, and room search. |
| tldraw-pricing | https://tldraw.dev/pricing | 2026-09-09 | Current hobby, trial, commercial-license, and sync packaging. Exact commercial price is not published and is not used. |
| icepanel-mcp | https://docs.icepanel.io/integrations/mcp-server.md | 2026-09-09 | Paid MCP read and write matrix for model objects, relationships, diagrams, flows, teams, technologies, tags, and ADRs; unsupported diagrams, drafts, versions, and comments. |
| drawio-mcp | https://github.com/jgraph/drawio-mcp/blob/main/README.md | 2026-09-09 | Official hosted MCP App, local MCP, assistant-plugin paths, supported diagram inputs and exports, and data-flow privacy matrix. Fetched with the GitHub file API. |
| excalidraw-mcp | https://github.com/excalidraw/excalidraw-mcp/blob/main/README.md | 2026-09-09 | Official remote, local, and self-deployed MCP App setup and interactive-canvas scope. Fetched with the GitHub file API. |
| mcp-apps | https://github.com/modelcontextprotocol/ext-apps/blob/main/README.md | 2026-09-09 | Official MCP Apps extension: `ui://` resources, sandboxed host rendering, bidirectional messaging, and host-compatibility boundary. Fetched with the GitHub file API. |
| penpot-mcp | https://help.penpot.app/mcp/ | 2026-09-09 | Remote and local integration, focused-page and one-tab boundaries, current tool set, read-before-write guidance, and self-hosted domain shape. |
| mermaid-flowchart | https://mermaid.js.org/syntax/flowchart.html | 2026-09-09 | Official flowchart nodes, edges, subgraphs, and layout-direction syntax. |
| mermaid-usage | https://mermaid.js.org/config/usage.html | 2026-09-09 | Official text-to-diagram rendering model, JavaScript package, browser usage, and default security configuration. |
| mermaid-architecture | https://mermaid.js.org/syntax/architecture.html | 2026-09-09 | Official architecture-diagram groups, services, junctions, edges, and current syntax. |
| mermaid-cli | https://github.com/mermaid-js/mermaid-cli/blob/master/README.md | 2026-09-09 | Official CLI installation, `.mmd` to SVG/PNG/PDF rendering, and Markdown transformation. Fetched with the GitHub file API. |
| crit-plans | https://crit.md/modes/plans-docs | 2026-09-09 | Crit's browser-rendered Markdown and Mermaid review loop, inline comments and suggestions, structured agent prompt, next-round diff, and branch state. |
| napkin-api | https://api.napkin.ai/ | 2026-09-09 | Asynchronous text-to-visual API, polling flow, export formats, account token, credits, and expiring download links. |
| structurizr-ai | https://docs.structurizr.com/ai/dsl-generation | 2026-09-09 | First-party sketch-to-Structurizr-DSL prompt examples and manual playground paste workflow. |
| localWhiteboardEvidence | sources/evidence.json | 2026-09-09 | Repository-local provenance for the consolidation coverage and the dated inference-control-plane Mermaid input at revision `a4a45cbe68c4eaef67f45bf8807605475fb23efa`. |
