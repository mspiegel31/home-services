---
name: household-config
description: "Owner-only: explain and request Hermes household configuration changes."
version: 1.0.0
author: home-services
license: MIT
metadata:
  hermes:
    tags: [config, household, owner, managed]
    category: household
---

# Household Configuration

This skill explains how Hermes household configuration works and how to
request changes. Messaging sessions (Signal and WhatsApp) run the restricted
toolset `web`, `vision`, `skills`, `todo` — no config or terminal tools — so
they can explain and request changes but not apply them. System changes go
through the CLI (the `hermes-cli` toolset) or the dashboard.

## How configuration ownership works

There are two classes of Hermes settings:

1. **Managed defaults and policy.** The `services/hermes/managed` snapshot in
   git is the source of truth for the default model and reasoning effort plus
   security-critical settings: native Signal/WhatsApp admission, restricted
   messaging toolsets, the no-messaging-admin sentinel and command allowlists,
   skills write approval, and the managed MCP server set. Config apply
   re-asserts these values. Durable changes go through git; admission identities
   stay in Portainer environment variables.

2. **User-set preferences.** Display preferences, session-scoped model choices,
   and personal skills may be changed from the CLI or dashboard. A session model
   override lasts for that session; the managed model remains the default for
   new sessions.

## The managed security contract

- **Admission is native.** The `SIGNAL_ALLOWED_USERS`/`SIGNAL_GROUP_ALLOWED_USERS`
  and the WhatsApp equivalents own who is admitted; no sender or group
  identity values are tracked in git.
- **Identical restricted messaging toolsets.** Signal and WhatsApp sessions get
  the same restricted set (`web`, `vision`, `skills`, `todo`); only the CLI has
  `hermes-cli`.
- **No messaging admins.** `allow_admin_from` and `group_allow_admin_from` are
  pinned to the `__no_messaging_admin__` sentinel, which no real identity can
  match: no messaging user is an admin, and every slash command outside the
  allowlists is denied to all messaging users.
- **Regular command allowlist.** Messaging users may only run `help`, `whoami`,
  `status`, `new` (the same list applies in groups).
- **Skills write approval.** `skills.write_approval` is pinned: skill writes
  stage for out-of-band review; gateway sessions have no inline approval
  channel.
- **Managed MCP surface.** `integrations.yaml` pins the allowed MCP server set.
  The main Mealie and Baby Buddy servers expose all native tools; resource and
  prompt wrappers stay disabled. Config apply and readiness reject any MCP
  server outside the managed set.

## Making a change

- **Preferences** (thinking text, session model, tone): update the active
  session and report what changed.
- **Managed defaults and policy** (default model/reasoning, admission variables,
  toolsets, admin sentinels, command allowlists, write approval, MCP sets):
  change `services/hermes/managed/` or the relevant Portainer admission value,
  then apply through GitOps.

## Guardrails

- If a managed value looks wrong, report it and ask for the managed change —
  do not paper over it with a local edit.
- Never remove the `__no_messaging_admin__` sentinels, widen the command
  allowlists, or add MCP servers outside the managed set. Readiness is
  fail-closed: a tampered or un-converged config drops the healthcheck.
- If you are not sure a change is managed or user-set, say so and I will check
  the managed snapshot before acting.
