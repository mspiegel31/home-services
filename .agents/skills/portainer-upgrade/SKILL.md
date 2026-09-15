---
name: portainer-upgrade
description: Upgrade Portainer server and agents (CE), with backup, update order, verification, and rollback. Use when the user asks to update Portainer, bump agent versions, fix version-mismatch warnings, switch CE to Business Edition, or roll back a failed update. Don't use for deploying application stacks, configuring environments, or Portainer license purchasing.
---

# Portainer Upgrade Procedure

Upgrade the Portainer server (this homelab: CE 2.39.x LTS at `192.168.1.51:9443`) and its agents, in the correct order, with a backup taken first. Portainer mutations through the MCP are silent on success — every step below is verified out-of-band.

**Hard rules:**
- Update **server first, then agents**. Portainer guarantees a new server talks to old agents, and most of the time an old server talks to new agents — but not always. Never do agents-only.
- Agent version should match server version ("when updating to X, make all agents X too").
- Take a backup **before** touching anything. Rollback is restore-from-backup; database schema bumps make newer DBs unusable by older versions.
- This repo is gitops: the Portainer *server* install itself lives outside this repo, so no repo changes are involved in a routine version upgrade.

## Fleet ground truth (re-resolve each time)

| env | id | agent | note |
|---|---|---|---|
| local | 2 | none | Portainer host; Docker socket — no agent to update |
| truenas | 25 | edge agent (Standard) | main host; converted from standard (18) 2026-09 |
| nvr | 24 | edge agent (Standard) | converted from standard (20) 2026-09 |
| ai | 22 | edge agent (Standard) | on inference-box `192.168.1.98` |

```
systemVersion()                     # ServerVersion, ServerEdition, UpdateAvailable
EndpointList(select="[].{id:Id,name:Name,type:Type,status:Status,agentVersion:AgentVersion,heartbeat:Heartbeat}")
```
Direct agents (`type` 1/2) read `status`; edge (`type` 4/7) read `heartbeat`.

## Step 0 — Backup

1. In Portainer UI: **Settings → Back up Portainer** (BE: built-in; CE: pull the `portainer_data` volume's `portainer.db`).
2. Confirm the backup file exists and note its path/version.

Rollback without a manual backup is possible only via the auto `backups/portainer.db.bak` in the `portainer_data` volume (DB only — no settings beyond the DB).

## Step 1 — Update the server

On the Portainer host (SSH; the host is not in `.omp/ssh.json`, ask the user for access):

```bash
docker stop portainer && docker rm portainer
docker pull portainer/portainer-ce:lts        # CE. BE would be portainer/portainer-ee:lts
docker run -d -p 9443:9443 --name=portainer --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data \
  portainer/portainer-ce:lts
```

Keep the host's existing port flags (9443 and **8000** — 8000 is the edge tunnel port, all three agent hosts poll through it; drop it only if you convert back to standard agents) and any `--sslcert/--sslkey` flags. The `portainer_data` volume preserves the database; Portainer migrates it on boot.

**In-app update (if BE):** Settings → update notification → Update now. In-app updates only offer **LTS** versions — STS requires manual image swap.

## Step 2 — Update the agents (one host at a time)

All three agent hosts (truenas, nvr, ai) run **Edge agents (Standard)**. Use the repo's upgrade script — it pulls the image first, then rebuilds the container while preserving `EDGE_ID`, `EDGE_KEY`, the `/data` volume (which persists the edge key), and all host bind mounts, including resolving Truenas's relocated docker root:

```bash
python3 /path/to/home-services/scripts/update_portainer_edge_agent.py --dry-run   # preview the docker run command
python3 /path/to/home-services/scripts/update_portainer_edge_agent.py --image portainer/agent:<version>
```

- `--image`: pin the tag to match the server version you just deployed (e.g. `portainer/agent:2.45.0`). `lts` (the default) tracks the newest LTS.
- `--edge-key <blob>`: only needed if the running container doesn't expose the key — copy it from Portainer: Environment → env → Edge information.
- `--no-insecure-poll`: only when the server cert is public-trusted (today it's self-signed, keep the default).
- If the new container fails to start, the script tells you to re-run with the previous `--image` — the endpoint and its data volume are intact.

Manual equivalent (only if the script can't run): `docker stop` + `docker rm` the agent, then `docker run` with the same `-e EDGE=1 -e EDGE_ID=… -e EDGE_KEY=… -e EDGE_INSECURE_POLL=1` env vars, the `/-:/host`, docker-sock, docker-volumes (use the resolved Truenas pool path), and named `/data` mounts, on `portainer/agent:<version>`. Capturing `EDGE_ID`/`EDGE_KEY` from the running container *before* removing it is mandatory.

UI-driven edge updates (admin → Update & Rollback, scheduled, with rollback) are **Business Edition only** — on CE, edge agents update manually as above.

## Step 3 — Verify

1. `systemVersion()` → `ServerVersion` is the target.
2. `EndpointList(select="[].{id:Id,name:Name,status:Status,heartbeat:Heartbeat,agentVersion:AgentVersion}")` → all direct agents `status: 1`, edge `heartbeat: true`, `agentVersion` matches the server.

**If the version looks unchanged** after a successful update: browser cache — hard-reload/incognito first, then check the container image tag.

## Step 4 — Rollback (only if the update broke something)

1. Stop and remove the Portainer container (do **not** delete `portainer_data`).
2. In `portainer_data`: rename `portainer.db` to `portainer.db.new`, copy `backups/portainer.db.bak` to `portainer.db`.
3. Start Portainer with the **previous** image version (must match the backed-up DB, or it refuses to start).
4. Re-run Step 2 with the previous agent version.

## Notes

- CE tracks its own release stream: CE 2.39.x LTS (2.39.5 → 2.39.7, security-only) and CE 2.45.0 LTS (Aug 2026, rolls up the 2.40–2.44 STS feature cycle incl. GitOps Sources/Workflows, alerting GA, backup improvements, CVE fixes). `portainer/portainer-ce` tags: `lts`/`latest` → 2.45.0; `2.39.7` → older LTS. In-app update only offers LTS.
- **CE → 2.45 unlocks**: the `/gitops/sources` + `/gitops/workflows` API (SourceID-based stack creation, polling, connection tests). BE-only extras on 2.45: UI-driven edge agent Update & Rollback, governance policies, KubeSolo onboarding. BE support: latest + 3 previous majors; CE: latest only.
- Do not update a single agent ahead of the server. Do not leave agents on the old version permanently.
- 1.x → 2.x jumps are not supported directly: go through 2.0.0 first.
- Sources: docs.portainer.io `/start/upgrade/` (docker, edge, tobe), `/faqs/upgrading/` (rollback, agent failures), `/faqs/getting-support/which-versions-of-portainer-do-you-provide-support-for.md`.
