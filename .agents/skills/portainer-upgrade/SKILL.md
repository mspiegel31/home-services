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
| truenas | 18 | standard agent, port 9001 | main host |
| nvr | 20 | standard agent, port 9001 | |
| ai | 22 | edge agent (Standard) | |

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

Keep the host's existing port flags (9443; 8000 only if edge agents poll through it) and any `--sslcert/--sslkey` flags. The `portainer_data` volume preserves the database; Portainer migrates it on boot.

**In-app update (if BE):** Settings → update notification → Update now. In-app updates only offer **LTS** versions — STS requires manual image swap.

## Step 2 — Update the agents (one host at a time)

**Standard agent** (truenas, nvr) — on each host:

```bash
docker stop portainer_agent && docker rm portainer_agent
docker pull portainer/agent:lts
docker run -d -p 9001:9001 --name portainer_agent --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:lts
```

Add `-e AGENT_SECRET=<value>` if the server runs with a custom `AGENT_SECRET` (default installs don't). Agents reconnect to the server; a brief "Disconnected" on the dashboard during the restart is expected.

**Edge agent** (`ai`): capture the env's **Edge identifier** and **Edge key** (Environment → ai → Edge information) *before* removing the container, then on the host:

```bash
docker stop portainer_edge_agent && docker rm portainer_edge_agent
docker pull portainer/agent:lts
docker run -d -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes -v /:/host \
  --restart always -e EDGE=1 -e EDGE_ID=<id> -e EDGE_KEY=<key> \
  --name portainer_edge_agent portainer/agent:lts
```

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

- CE support policy: latest release only. BE: latest + 3 previous majors.
- **CE → BE switch**: in-app from 2.17 (Settings → upgrade) or swap the image to `portainer/portainer-ee:lts` with the license; config carries over. Agent-only deployments need no BE agent.
- Do not update a single agent ahead of the server. Do not leave agents on the old version permanently.
- 1.x → 2.x jumps are not supported directly: go through 2.0.0 first.
- Sources: docs.portainer.io `/start/upgrade/` (docker, edge, tobe), `/faqs/upgrading/` (rollback, agent failures), `/faqs/getting-support/which-versions-of-portainer-do-you-provide-support-for.md`.
