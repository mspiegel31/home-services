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

This skill is for the OWNER profile only. Non-owner profiles do not have the
config/terminal tools, so this skill will not run for them.

## How configuration ownership works

There are two classes of Hermes settings:

1. **Managed policy.** The `services/hermes/managed` snapshot in git is the source
   of truth for security-critical settings: the WhatsApp allowlists, profile
   routing, the restricted tool surfaces for the spouse and family profiles, and
   the `household-auth` principal policy. These values are re-asserted on every
   config apply. If you change one directly on the machine, the next apply
   restores it. To change managed policy durably, change it in git and push.

2. **User-set preferences.** Everything else (display preferences like thinking
   text, model choice per profile, personal skills) is yours to set from chat.
   These persist and are not overridden by config apply.

## Making a change

- **Preferences** (thinking text, model, tone): just say so. I will update the
  config for your profile and confirm what changed.
- **Managed policy** (allowlists, routing, restricted toolsets, principals): I
  will not edit these on the machine. I will tell you what to change in
  `services/hermes/managed/` and that it takes effect on the next config apply or
  gateway restart. I can prepare the exact diff for you to review and commit.

## Guardrails

- If a managed value looks wrong, report it and ask for the managed change —
  do not paper over it with a local edit.
- Never disable the household-auth plugin or empty the principals allowlist.
  The gateway refuses to start without a bound owner identity (fail-closed).
- If you are not sure a change is managed or user-set, say so and I will check
  the managed snapshot before acting.
