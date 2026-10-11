---
name: portainer-stack-env
description: Update environment variables on an existing Portainer stack - add or rotate a secret (provider keys, tokens), the full-replacement semantics of PUT /stacks/{id}, the git-to-file-based conversion trap that wipes GitConfig and auto-update, recovering write-only secret values from running containers, restoring the git binding via delete+recreate, and the env-before-push ordering for ${VAR:?} compose interpolation. Use when the user asks to set, add, rotate, or fix a stack's env variables in Portainer, or when a stack lost its GitConfig/AutoUpdate after an API update. Not for creating stacks or ordinary commit-push redeployments (see portainer-gitops-stack).
---

# Portainer Stack Environment Variables

Verified live 2026-10-11 on CE 2.45.0 while adding `PROVIDER_KEY_SMALL` to the
`omni-provider` stack. Stack env vars are the values Portainer interpolates
into `${VAR}` references in the compose file; per repo rule they live in
Portainer, never in Git.

## The four facts that cause every incident

1. **`Env` on update is a full replacement, not an upsert.** Any variable not
   in the PUT payload is deleted. A compose `${MISSING:?...}` then fails
   interpolation and the *whole stack* redeploy fails - taking down unrelated
   services in the same stack.
2. **`PUT /stacks/{id}` on a compose stack requires `stackFileContent`**
   (400 "Invalid stack file content" without it) **and deliberately converts
   a git-tracked stack to file-based**: `updateComposeStack`
   (`api/http/handler/stacks/stack_update.go`) stops the auto-update job and
   nulls `GitConfig`/`AutoUpdate`. There is no payload field that preserves
   the binding.
3. **`POST /stacks/{id}/git` only mutates an *existing* binding** - on a
   converted stack it 500s "No Git config in the found stack" - and requires
   `Interval` or `Webhook`.
4. **Secret values are write-only through MCP** (redacted), but the direct
   API returns them: `https://192.168.1.51:9443/api/stacks/{id}` with
   `X-API-Key: $(cat ~/.config/agent-secrets/portainer-api-key)` and `-k`.
   The running container's `Config.Env` is the ground truth when in doubt -
   note the container env name may differ from the stack var name (compose
   maps them, e.g. `PROVIDER_KEY` -> `OMNI_SERVICE_ACCOUNT_KEY`).

## Preferred path

If an operator is present, have them edit in the UI (stacks -> stack ->
Editor -> Environment). It preserves the git binding. Use the API path only
when they are not.

## API procedure (when the operator is absent)

Ordering rule: **set the env before pushing any compose change that
references the new `${VAR:?}`** - the 5m git poll would otherwise redeploy
with a missing variable and fail the whole stack.

1. Read current env *names*: `StackInspect` (MCP is fine; values redacted).
2. Recover current *values* for every existing var - direct API GET, or on
   the target host:
   `docker inspect <container> --format '{{range .Config.Env}}{{println .}}{{end}}'`
   and map back through the compose file.
3. Build the payload **without echoing secrets**: values via env vars into a
   `python3 -c`/jq one-liner writing a mode-600 file; `curl --data @file`.
   Never in argv, logs, or chat.
   `{"stackFileContent": "<current compose from git: git show origin/main:<path>>",
     "Env": [ ...all vars, real values, plus the new one... ]}`
4. `PUT /api/stacks/{id}?endpointId=<N>`. This redeploys the stack.
5. **Check the damage**: `StackInspect` for `GitConfig`/`AutoUpdate`. If
   null, the binding is gone - restore it below.

## Restoring a wiped git binding

The UI's reconfigure is the only in-place path; via API it is
delete-then-recreate (brief undeploy - containers stop, then come back):

1. `DELETE /api/stacks/{id}?endpointId=<N>` - plain. (`external=true` hit
   "This node is not a swarm manager" on the compose edge env; the plain
   delete 204s and undeploys.)
2. `POST /api/stacks/create/standalone/repository?endpointId=<N>` with
   `{"Name": "<same name>", "RepositoryURL": "https://github.com/mspiegel31/home-services",
     "RepositoryReferenceName": "refs/heads/main", "ComposeFile": "<path>",
     "AutoUpdate": {"Interval": "5m"}, "Env": [ ...full list again... ]}`.
   Same name -> same compose project -> containers rebuild cleanly.
3. Verify: `GitConfig.ConfigHash` = current HEAD, `AutoUpdate.Interval` set,
   all env names present, containers `Up`, and the service's own health
   check (e.g. `omnictl infraprovider list` shows `connected=true`).

## Notes

- Two processes claiming one identity fight (e.g. a throwaway provider
  container plus the stack service): retire the throwaway once the stack
  service is verified.
- Keep a mode-600 recovery copy of any minted key on the management host
  (e.g. `/mnt/tank/container-configs/<stack>/provider-key.env`) so a wiped
  Portainer env is recoverable.
- Stack creation and redeploy mechanics: `portainer-gitops-stack`.
