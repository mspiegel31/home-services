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

## Step 1 — Resolve the environment ID

```
EndpointList(select="[].{id:Id,name:Name,type:Type,status:Status}")
```

Pick the ID whose `name` matches the target. Direct agents (`type` 1/2) must have `status: 1`.

## Step 2 — Check for an existing stack with the same name

```
StackList(select="[].{id:Id,name:Name,git:GitConfig}", filters="{\"EndpointID\": 18}")
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
2. **Containers up**: list containers on the environment and check the project's containers are `running`:

```
docker_proxy(environment_id=<id>, path="/containers/json?filters={\"label\":\"com.docker.compose.project=<stack name>\"}", select="[].{name:Names[0],state:State,status:Status}")
```

`created`/`exited` states mean the deploy broke — fetch the failing container's logs (`/containers/{id}/logs?stdout=true&stderr=true&tail=100`) and diagnose. Image pulls can take minutes on first deploy; `created` with an `ImagePull` status is transient, not a failure.

Report: stack ID, environment, compose path, and container states.

## Failure cleanup

If the stack created but deployed broken, remove it by ID: `StackDelete(id=<id>)` (returns `{"Output":""}` on success — verify it's gone via `StackList`). Then fix the compose file in the repo, push, and recreate.

## Notes
- The installed CE 2.39.5 has no GitOps Sources API (`GitOpsSourcesList` / `GitOpsSourcesCreateGit` 404), so the deprecated `Repository*` fields on the stack-create tools are the working path — do not attempt the SourceID flow. CE 2.45.0+ registers the sources/workflows routes unconditionally, so after a server upgrade to 2.45 the SourceID flow becomes the preferred path (one source for the repo, stacks reference it).
- Media app convention (repo rule): configs/data belong under `/mnt/tank/container-configs/<APP_NAME>` on truenas; the compose file should already encode this.
- Repo rule: no `env_file` in Portainer repo stacks. If a compose file uses `env_file`, fix the compose file in the repo (declare `${VAR}` explicitly) before deploying.
