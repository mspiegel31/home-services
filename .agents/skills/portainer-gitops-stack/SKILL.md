---
name: portainer-gitops-stack
description: Create, verify, and update GitOps repository-tracked Docker stacks in Portainer via the Portainer MCP tools (StackCreateDockerStandaloneRepository). Use when the user asks to add, deploy, or recreate a home-services stack on a Portainer environment (truenas, nvr, ai, local), or to point an existing stack at a new compose path. Don't use for container-level docker operations, Kubernetes stacks, or editing Portainer settings.
---

# Portainer GitOps Stack Creation

Create a repository-tracked Docker stack on a Portainer environment using the Portainer MCP tools. The stack tracks `https://github.com/mspiegel31/home-services` (public, no auth) and pulls its compose file from the repo — never inline content. All changes to running stacks happen by committing to the repo, then redeploying through Portainer; never make live edits to Portainer stacks unless explicitly debugging.

## Inputs

Collect or derive before creating:

- **Stack name** — usually the service name, matching the `services/<name>/` directory.
- **Compose path** — `services/<name>/docker-compose.yml` relative to the repo root. For multi-file stacks, pass extra files via `AdditionalFiles`.
- **Environment** — where the stack runs. Default to `truenas` (the main host); use `local`/`nvr`/`ai` only when the user names one. Resolve the numeric ID fresh each time (see Step 1); never guess.
- **Env vars** — the `${VAR}` references declared in the compose file. Per repo rule, values live in Portainer, not in the repo: pass them as the `Env` array. Read the compose file to find the variable names.
- **Branch** — `refs/heads/main` unless told otherwise.

## Step 0 — Verify the compose file exists in the repo

The stack deploys from the remote repo, so the compose file must be committed **and pushed** on the target branch before creating the stack. Verify both:

```
git ls-remote https://github.com/mspiegel31/home-services main   # branch exists on remote
git status services/<name>/docker-compose.yml                     # clean = pushed
```

If the file is missing or uncommitted, stop: commit + push first. A stack created against an absent path fails at deploy with a null `ConfigHash` (see Step 4).

**Pre-flight compose sanity check** (cheap, saves a full deploy cycle). Before creating, scan the compose for the recurring traps in this repo:
- **LSIO images** (`lscr.io/linuxserver/*`): never set `init: true` — s6-overlay is the entrypoint and needs to be PID 1; an injected tini causes an `s6-overlay-suexec: fatal: can only run as pid 1` crash loop. Remove `init: true`.
- **Public port**: LSIO images front the app with **nginx on container port 80** (the backend listens on loopback, e.g. `127.0.0.1:3000`). Map the host port to container port **80**, not the backend port. If unsure, check `docker top` / the running processes.
- **Healthcheck path**: the `wget --spider` target must be a route that exists in that version and must use `127.0.0.1` (not `localhost` — on some images it resolves to IPv6 `::1` → connection-refused). Probe the live app with `curl` to confirm which path returns 200 (e.g. babybuddy v2.10 has no `/health/`; `/login/` returns 200).

## Step 1 — Resolve the environment ID

```
EndpointList(select="[].{id:Id,name:Name,type:Type,status:Status}")
```

Pick the ID whose `name` matches the target. For direct agents (`type` 1/2) `status: 1` means up; for edge agents (`type` 4/7) `status` is cosmetic — check `heartbeat` / `LastCheckInDate` instead.

## Step 2 — Check for an existing stack with the same name

```
StackList(select="[].{id:Id,name:Name,git:GitConfig}", filters="{\"EndpointID\": <id from step 1>}")
```

If a stack with the target name exists, stop: ask whether to update it (use `StackUpdate` / delete+recreate) instead of creating a duplicate.

## Step 3 — Create the stack

```
StackCreateDockerStandaloneRepository({
  endpointId: <id from step 1>,
  Name: "<stack name>",
  RepositoryURL: "https://github.com/mspiegel31/home-services",
  RepositoryReferenceName: "refs/heads/main",
  ComposeFile: "services/<name>/docker-compose.yml",
  Env: [{name: "VAR", value: "..."}]
})
```

- Public repo → leave all `Repository*Authentication*` fields unset. Never invent credentials.
- This tool returns the new stack ID. The creation response alone is not proof of deployment — Portainer mutates silently.

## Step 4 — Verify the deploy

1. **Config hash advanced**: `StackList` with the endpoint filter again; the new stack's `git.ConfigHash` must be non-null. A null hash means the clone/checkout failed (wrong path, unpushed file, bad branch).
2. **Containers up**: list containers and filter client-side — the `filters` query param is rejected (`invalid filter`) and query strings must go in `query_params`, not in `path`:

```
docker_proxy(environment_id=<id>, path="/containers/json", select="[].{name:Names[0],state:State,status:Status}")
```

Filter the list for `<stack name>` on the client.

`created`/`exited` states mean the deploy broke — fetch the failing container's logs (`/containers/{id}/logs` with `query_params: {"stdout": "true", "stderr": "true", "tail": "100"}`) and diagnose. Image pulls can take minutes on first deploy; `created` with an `ImagePull` status is transient, not a failure.
`running` is necessary, not sufficient — for a healthy service the status should read `healthy`, not `unhealthy`. The list view omits the `Health` object; to read it, hit `/containers/{id}/json` with `select="{health:State.Health.Status}"`. The container **ID changes on every redeploy** — re-resolve it from `/containers/json` each time.

Report: stack ID, environment, compose path, and container states.

## Redeploy after changes (commit → push → redeploy)

Once a stack is created, the only way to change it is the gitops loop: fix the compose in the repo, `git push`, then re-apply the ref:

```
StackGitRedeploy({ id: <stack id>, endpointId: <endpoint id from Step 1>, Prune: false })
```

- `StackGitRedeploy` **requires `endpointId`** — omitting it 404s with `Unable to find the environment … (key=0)`. Pass the endpoint id from Step 1.
- Confirm the response's `GitConfig.ConfigHash` / `CurrentDeploymentInfo.ConfigHash` advanced to the new commit.
- Then re-run Step 4's container check.

## Failure cleanup

If the stack created but deployed broken, remove it by ID: `StackDelete(id=<id>)` (returns `{"Output":""}` on success — verify it's gone via `StackList`). Then fix the compose file in the repo, push, and recreate.

## Troubleshooting: "Unable to open the tunnel" (edge agent wedged)

Signature: heartbeats are green (`heartbeat: true`, fresh `LastCheckInDate`) but **every** command to that edge env — reads and writes — returns `HTTP 500 … Unable to open the tunnel` / `Unable to get the active tunnel`, while other edge envs (e.g. nvr) work fine. This is a stuck edge command channel, **not** a bad argument.

Root cause seen: the Portainer server's SSH host key rotated (server redeploy), so the edge env's baked `EDGE_KEY` fingerprint no longer matches → the agent's ssh handshake fails with `Invalid fingerprint`. `docker restart` does **not** fix it (the stale fingerprint lives in the agent's env/key, not the container state).

Fix (on the target host, as root):
1. In the Portainer UI, **Dissociate** the environment, then **re-associate** it — regenerates the edge key with the current fingerprint. The endpoint id, its stacks, and their Portainer-side env vars are preserved; only the connection key changes. Do NOT "Delete environment".
2. Re-run the agent container with the new key (same mounts/volume/`EDGE_ID`, new `EDGE_KEY`):
   ```
   docker stop portainer_edge_agent && docker rm portainer_edge_agent
   docker run -d --name portainer_edge_agent --restart always \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v /var/lib/docker/volumes:/var/lib/docker/volumes \
     -v /:/host -v portainer_agent_data:/data \
     -e EDGE=1 -e EDGE_ID=<edge id> -e EDGE_KEY=<new key> -e EDGE_INSECURE_POLL=1 \
     portainer/agent:2.45.0
   ```
3. Confirm `docker logs portainer_edge_agent` shows no `Invalid fingerprint`, then re-test a read.

`docker_proxy` is the cheapest tunnel probe: `docker_proxy(environment_id=<id>, path="/containers/json", select="[].{name:Names[0]}")`.

## Notes
- Versions: the CE server is **2.45.0** (truenas agent 2.45.0; ai/nvr agents still 2.39.5). The deprecated inline `Repository*` fields on the stack-create tool work across all of these and are the reliable path. CE 2.45.0+ registers the GitOps Sources API, so once all agents are on 2.45 the SourceID flow (one source for the repo, stacks reference it) becomes the preferred path.
- **MCP update is part of the Portainer update process.** The Portainer MCP server (`mcp-portainer`, a uvx stdio server) tracks the CE API, so when the Portainer server (or its agents) is upgraded, bump the MCP version with it. Currently: the personal profile pins `mcp-portainer~=2.45.1` in `~/dotfiles/dot_omp/private_profiles/private_personal/private_agent/private_mcp.json` (chezmoi → `~/.omp/profiles/personal/agent/mcp.json`). To update: bump the pin, `chezmoi apply`, commit + push the dotfiles repo, then `/mcp reload` (or restart omp) so the new version boots. Verify with `uvx --from "mcp-portainer~=X" python -c "import importlib.metadata as m; print(m.version('mcp-portainer'))"`. A too-old MCP against a newer CE server surfaces as schema/behavior gaps (e.g. 2.44 didn't surface the `endpointId` requirement on `StackGitRedeploy`; 2.45.1 does).
- Media app convention (repo rule): configs/data belong under `/mnt/tank/container-configs/<APP_NAME>` on truenas; the compose file should already encode this.
- Repo rule: no `env_file` in Portainer repo stacks. If a compose file uses `env_file`, fix the compose file in the repo (declare `${VAR}` explicitly) before deploying.
