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

1. **Managed policy.** The `services/hermes/managed` snapshot in git is the
   source of truth for security-critical settings: the native Signal/WhatsApp
   admission, the restricted messaging toolsets, the no-messaging-admin
   sentinel and command allowlists, the skills write-approval setting, and the
   bounded MCP server and tool sets. These values are re-asserted on every
   config apply. If you change one directly on the machine, the next apply
   restores it. To change managed policy durably, change it in git and push.
   The admission allowlists themselves live in container environment variables
   (Portainer values), not in git.

2. **User-set preferences.** Everything else (display preferences like thinking
   text, model choice, personal skills) is yours to set from the CLI or
   dashboard. These persist and are not overridden by config apply.

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
- **Bounded MCP surface.** `integrations.yaml` pins the MCP server set and the
  bounded per-server tool include lists. Config apply and the readiness check
  refuse any MCP server outside that set — fail-closed: the healthcheck drops
  to unhealthy until the rogue entry is removed and the next apply converges.

## Making a change

- **Preferences** (thinking text, model, tone): just say so. I will update the
  config and confirm what changed.
- **Managed policy** (admission variables, toolsets, admin sentinels, command
  allowlists, write approval, MCP sets): I will not edit these on the machine.
  I will tell you what to change in `services/hermes/managed/` (or in the
  admission environment variables for who is admitted) and that it takes effect
  on the next config apply or gateway restart. I can prepare the exact diff for
  you to review and commit.

## Guardrails

- If a managed value looks wrong, report it and ask for the managed change —
  do not paper over it with a local edit.
- Never remove the `__no_messaging_admin__` sentinels, widen the command
  allowlists, or add MCP servers outside the managed set. Readiness is
  fail-closed: a tampered or un-converged config drops the healthcheck.
- If you are not sure a change is managed or user-set, say so and I will check
  the managed snapshot before acting.
