---
name: portainer-stack-urls
description: Build clickable Portainer stack deep links for this homelab via scripts/portainer_stack_url.py. Use when the user asks for a link, deep link, permalink, or URL to a Portainer stack, environment, or container — typically alongside stack diagnostics so they can click through. Resolve real stack and endpoint IDs through the Portainer MCP rather than guessing. Don't use for creating or redeploying stacks (portainer-gitops-stack) or server/agent updates (portainer-upgrade).
---

# Portainer Stack Deep Links

Portainer's UI routes on the client (ui-router behind a `#!/` hash), so the API and MCP never return UI links — assemble them with `scripts/portainer_stack_url.py` (pure formatter, no auth):

    ./scripts/portainer_stack_url.py glance --id 218 --endpoint 2
    # https://192.168.1.51:9443/#!/2/docker/stacks/glance?id=218&type=2&regular=true

## Get the IDs from the MCP, never guess

A wrong `endpointId` 404s the environment; a wrong `id` renders an empty detail page with no error. One `StackList` call returns everything the script consumes — project it to three fields and pipe:

    StackList(select="[].{id:Id,name:Name,endpoint:EndpointId}")

Save that JSON and feed it: `./scripts/portainer_stack_url.py --json - --label < stacks.json`. `--label` prefixes each URL with `env/name (id)` so a stale ID is visible at a glance. Filter with a JMESPath test (`[?name=='plex']`) when the user named a stack.

## Options

- `--tab editor` jumps to the stack editor (webhooks live there); default tab is info.
- `--container <id>` deep links into one container of the stack.
- `--type swarm|kubernetes` for non-compose stacks; every `services/*/docker-compose.yml` stack here is the default `compose`.
- `--external` / `--orphaned` for stacks in those modes; `--base` overrides the Portainer URL (also `PORTAINER_URL` env) if the server ever moves.

## Delivery

Emit full URLs, one per line or in a table column — never a template the user fills in. The base is self-signed on `:9443` (plain HTTP `:9000` is closed), so headless fetches need certificate verification off.
