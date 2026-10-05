# Paperclip home platform trial with a portable work-local stack

## Context

Deploy a working Paperclip application on TrueNAS through the existing Portainer CE repository-stack workflow. The same service directory and Docker Compose file must run independently on a work/local Docker host, using different values and credentials rather than a home-specific deployment fork. Acceptance is the application platform only: authenticated ownership, company/project/issue CRUD, persistent state, restart, and local portability. OpenCode must be present but no agents, model/GitHub credentials, scheduled agent jobs, or operations permissions are configured.

The user selected LAN/VPN-only **HTTP**, one owner account, stock upstream execution with agents unconfigured, and **PR review before deployment from merged main**. Future unattended operations must have bounded authority; this installation does not authorize those operations or claim to isolate an OpenCode child process from Paperclip's own state.

## Approach

### 1. Establish an isolated implementation lane and fixed runtime inputs

Work from `/Users/michaelspiegel/development/personal/home-services`. The observed checkout is on `chore/litellm-per-model-config-split` with untracked `LITELLM_PER_MODEL_CONFIG_SPLIT_PLAN.md`; leave both untouched. After plan approval, fetch `origin/main` and create branch `feat/paperclip-home-trial` in `.slim/worktrees/paperclip-home-trial`, based on the fetched main, not the current feature branch. `.gitignore` already excludes `.slim/worktrees/` and `.slim/worktrees.json`; `.ignore` already permits their inspection. Register the lane in the local worktree manifest without committing that metadata. Existing stale worktree registrations are unrelated: do not prune them.

Commands, after checking branch/path availability and the existing worktree list:

```sh
git fetch origin main
git worktree add -b feat/paperclip-home-trial .slim/worktrees/paperclip-home-trial origin/main
```

If that branch/path already exists at execution, do not reset or delete it. Use the same branch/path names with a UTC `-YYYYMMDD-HHMMSS` suffix and record the actual lane in the PR. All implementation edits and local qualification below run in that lane.

For `.slim/worktrees.json`, preserve any existing entries. If absent, create `{ "version": "1.0", "updatedAt": "<UTC timestamp>", "lanes": [] }`; append one lane with `slug` equal to the chosen path basename, the actual `branch` and `path`, `base` equal to the fetched main commit SHA, `purpose: "Paperclip portable home platform"`, `owner: "orchestrator"`, `status: "active"`, and `createdAt` set to the same UTC timestamp. This is local workflow state, not a fourth committed service file.

Use these **manifest-index** pins, already inspected read-only and confirmed to include linux/amd64 and linux/arm64:

- `ghcr.io/paperclipai/paperclip:2026.916.1@sha256:a02ac35ac41df911af477422ea0e781cf41d2b2c600c66f0a5ac9d8c63f52c2c`
- `postgres:17.10-alpine@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193`

Do not add a `platform: linux/amd64` override: TrueNAS is x86_64 and the available local workstation is ARM64. The Paperclip image already contains OpenCode, curl, git, and GitHub CLI; no derived image or upstream repository checkout is needed. Keep the upstream tini/entrypoint: it performs initial volume ownership repair as root and then runs the application as `node` UID/GID 1000. Do not add Compose `init: true`, override the entrypoint, force `user:`, or drop the capabilities needed by its ownership/UID transition.

Runtime/bootstrap facts were checked against tag `v2026.916.1`, not inferred from current master: [Dockerfile](https://github.com/paperclipai/paperclip/blob/v2026.916.1/Dockerfile), [entrypoint](https://github.com/paperclipai/paperclip/blob/v2026.916.1/scripts/docker-entrypoint.sh), [server configuration](https://github.com/paperclipai/paperclip/blob/v2026.916.1/server/src/config.ts), [startup/migrations](https://github.com/paperclipai/paperclip/blob/v2026.916.1/server/src/index.ts), [authentication](https://github.com/paperclipai/paperclip/blob/v2026.916.1/server/src/auth/better-auth.ts), and [health](https://github.com/paperclipai/paperclip/blob/v2026.916.1/server/src/routes/health.ts).

### 2. Add the self-contained app/database service

Create `services/paperclip/docker-compose.yml`, with exactly two services, `paperclip` and `db`, and `name: paperclip`. Do not add model gateways, Redis, cron services, git-sync, Cloudflare networks, SSH runners, Kubernetes/sandbox plugins, OMP, or a GitHub App in this platform installation.

Use `services/mealie/docker-compose.yml` as the repository precedent for PostgreSQL 17.10, explicit required env interpolation, `pg_isready`, durable mounts, and resource limits. Unlike its fixed home paths, make this stack's entire data root configurable. `services/inbox-zero/docker-compose.yml` supplies the existing `depends_on: condition: service_healthy` app/database pattern. No equivalent Paperclip stack was found.

Implement this concrete service contract:

| Setting | `paperclip` | `db` |
|---|---|---|
| Image | Paperclip pin above | PostgreSQL pin above |
| Restart | `unless-stopped` | `unless-stopped` |
| Resource limits | memory `4G`, CPUs `2.0` | memory `1G`, CPUs `1.0` |
| Security | `no-new-privileges:true`; no privileged mode, no extra capabilities, no host socket | `no-new-privileges:true`; no privileged mode, no host port |
| PID limit | `2048` | Leave upstream/Docker default |
| Bind mount | `${PAPERCLIP_DATA_DIR:?Set an absolute PAPERCLIP_DATA_DIR}/app:/paperclip` | `${PAPERCLIP_DATA_DIR:?Set an absolute PAPERCLIP_DATA_DIR}/postgres:/var/lib/postgresql/data` |
| Host port | `${PAPERCLIP_BIND_IP:-127.0.0.1}:${PAPERCLIP_PORT:-3100}:3100` | None |
| Networks | `application`, `database` | `database` only |
| Dependency | `db` with `condition: service_healthy` | None |
| Healthcheck | `CMD curl --fail --silent --show-error http://127.0.0.1:3100/api/health`; interval 30s, timeout 5s, retries 5, start period 90s | `CMD-SHELL pg_isready -U paperclip -d paperclip`; interval 10s, timeout 5s, retries 10, start period 30s |

Declare stack-scoped `application` as an ordinary bridge and `database` with `internal: true`. Do not set globally named networks or `container_name`, so a second installation can use a different Compose project name without collisions. Database persistence is a separate directory from the app; it is not mounted into the app container. The app still holds its own database credentials, so this is not a sandbox boundary for later local agents.

Set `db.environment` exactly:

- `POSTGRES_DB: paperclip`
- `POSTGRES_USER: paperclip`
- `POSTGRES_PASSWORD: ${PAPERCLIP_POSTGRES_PASSWORD:?Set a URL-safe hexadecimal database password}`

Set the app environment explicitly (quote booleans/numeric strings in YAML):

| App environment key | Value |
|---|---|
| `PAPERCLIP_DEPLOYMENT_MODE` | `authenticated` |
| `PAPERCLIP_DEPLOYMENT_EXPOSURE` | `private` |
| `PAPERCLIP_AUTH_BASE_URL_MODE` | `explicit` |
| `PAPERCLIP_PUBLIC_URL` | `${PAPERCLIP_PUBLIC_URL:?Set the canonical URL including scheme and port}` |
| `DATABASE_URL` | `postgresql://paperclip:${PAPERCLIP_POSTGRES_PASSWORD:?Set a URL-safe hexadecimal database password}@db:5432/paperclip` |
| `PAPERCLIP_MIGRATION_AUTO_APPLY` | `true` |
| `BETTER_AUTH_SECRET` | `${BETTER_AUTH_SECRET:?Set a persistent authentication secret}` |
| `PAPERCLIP_AGENT_JWT_SECRET` | `${PAPERCLIP_AGENT_JWT_SECRET:?Set a persistent agent signing secret}` |
| `PAPERCLIP_TOOL_ACTION_SIGNING_SECRET` | `${PAPERCLIP_TOOL_ACTION_SIGNING_SECRET:?Set a persistent tool-action signing secret}` |
| `PAPERCLIP_SECRETS_MASTER_KEY` | `${PAPERCLIP_SECRETS_MASTER_KEY:?Set a persistent 32-byte hexadecimal encryption key}` |
| `PAPERCLIP_SECRETS_STRICT_MODE` | `true` |
| `PAPERCLIP_AUTH_DISABLE_SIGN_UP` | `${PAPERCLIP_AUTH_DISABLE_SIGN_UP:-true}` |
| `HEARTBEAT_SCHEDULER_ENABLED` | `${HEARTBEAT_SCHEDULER_ENABLED:-false}` |
| `PAPERCLIP_TELEMETRY_DISABLED` | `1` |
| `PAPERCLIP_ANNOUNCEMENTS_ENABLED` | `false` |

Leave baked-in `HOST`, `PORT`, `HOME`, `PAPERCLIP_HOME`, `PAPERCLIP_CONFIG`, and `SERVE_UI` unchanged. Leave `PAPERCLIP_MANAGED_CONFIG` entirely absent: an empty variable is not an acceptable substitute. Do not set `TRUST_PROXY`; this deployment has no reverse proxy. The canonical public URL supplies the accepted hostname; no extra hostname allowlist is required.

There must be **no Compose service `env_file` directive**. Local `docker compose --env-file .env` is interpolation input and is allowed; Portainer supplies the same declared values through its stack Env array. Do not add provider API keys, PATs, host credential homes, or the user's source checkout as mounts.

The four application secrets plus the database password are independent `openssl rand -hex 32` values; `PAPERCLIP_SECRETS_MASTER_KEY` is thus 32 bytes represented as 64 hex characters. Never emit actual values into committed files, PR text, screenshots, or final chat. Do not regenerate values when recreating an existing installation. Existing authenticated-mode secret handling and the tool-action key's exact call-time enforcement need not be reimplemented; supplying stable independent keys is the chosen contract.

Keep upstream housekeeping defaults, including built-in database backups, unchanged; do not add a backup service or agent routine. Persist the full app home along with the separate database state. A database dump alone does not restore file attachments or secret-decryption keys.

### 3. Define the portable operator/bootstrap interface

Create `services/paperclip/.env.example` with comments and these exact keys. Nonsecret values are:

```dotenv
PAPERCLIP_BIND_IP=127.0.0.1
PAPERCLIP_PORT=3100
PAPERCLIP_PUBLIC_URL=http://localhost:3100
PAPERCLIP_DATA_DIR=
PAPERCLIP_AUTH_DISABLE_SIGN_UP=true
HEARTBEAT_SCHEDULER_ENABLED=false
```

Also include blank required entries for `PAPERCLIP_POSTGRES_PASSWORD`, `BETTER_AUTH_SECRET`, `PAPERCLIP_AGENT_JWT_SECRET`, `PAPERCLIP_TOOL_ACTION_SIGNING_SECRET`, and `PAPERCLIP_SECRETS_MASTER_KEY`. Blank values must fail Compose interpolation before containers start. Explain that the data directory is an absolute, writable path outside the checkout; work/local users can use `$HOME/.local/share/paperclip` after expanding `$HOME` when writing the value. The file is a template, never a source of generated credentials.

Create `services/paperclip/README.md` as the runnable installation contract for another agent/operator. It must give:

1. The two images/architectures, resource caps, required Docker Compose support, and application-only scope. No Portainer, home DNS, tunnel, shared gateway, or home-services Git access is needed to run the copied folder locally; initial image retrieval still needs registry access.
2. A variable table separating the five key/password entries from nonsecret values, with independent random-value generation instructions, `chmod 600 .env`, and the root `.gitignore` rule already protecting `.env`. Explain that shell variables override `.env`; remove unintended exported values when switching installs.
3. Exact local commands from `services/paperclip/`:

   ```sh
   docker compose --env-file .env config --quiet
   PAPERCLIP_AUTH_DISABLE_SIGN_UP=false docker compose --env-file .env up -d --wait --wait-timeout 300
   # Create/claim the first owner through the browser before the next command.
   docker compose --env-file .env up -d --wait --wait-timeout 300
   ```

   `.env` retains `PAPERCLIP_AUTH_DISABLE_SIGN_UP=true`; the inline false override exists only for first bootstrap. Do not run the open-signup command against an already claimed installation during routine upgrades.
4. Open the configured canonical URL, create one owner account, and use the documented private-install **Claim this instance** action or the one-time board-claim URL in startup output if that release displays it. Claim URLs and passwords are sensitive; never paste them in PR/chat. Verify `/api/health` changes from `bootstrap_pending` to `ready`. Then close signup as above. The owner chooses their own email/password in the browser; do not hardcode a user account in Compose.
5. Create a blank company/project without completing the UI's hire-an-agent/model wizard. The deterministic API path is specified in Verification below. No CEO/built-in agent is automatically seeded by blank company creation in this release. Do not set up a model just to dismiss onboarding.
6. Shutdown/recreate commands preserve mounted data; never use volume/data deletion as a troubleshooting step. Preserve signing/encryption/database secrets on upgrades. A database-password env change does not rotate the password in an existing PostgreSQL data directory.
7. TrueNAS values and the GitOps/owner-bootstrap sequence in step 5 below, plus work-local reconfiguration: change only data root, bind address/port, canonical URL, and secrets. GitHub/model setup is not required to boot or pass this platform acceptance. Do not claim that provisioning a GitHub App alone makes the self-hosted agent connector work.
8. Explicit security boundary: HTTP is accepted only on trusted LAN/VPN; there is no OIDC or TLS layer added here. One owner, signup closed after bootstrap. No configured agents/connections/secrets for operations. `HEARTBEAT_SCHEDULER_ENABLED=false` disables timers, not every API-driven wake; zero agents and absent credentials are the primary dormant posture. Later agents require a separate decision about secrets, execution isolation, and target/action allowlists. OpenCode running locally would share app-container authority.

No setup script, custom adapter, generated skill/context file, image-build workflow, or repository-wide CI change is required for this three-file package. Existing `renovate.json` already enables digest maintenance for Compose images; retain the reviewed pins and manual deployment workflow.

### 4. Qualify locally, publish a focused PR, and wait for main

Run all local Verification checks below before opening the PR. Local Docker CLI/Compose were present during planning, but Docker Desktop's daemon was stopped. On approved execution, start Docker Desktop if needed (`open -a Docker` on this workstation) and wait for the daemon to become reachable; this is a prerequisite, not a reason to replace local portability verification with a TrueNAS-only run.

Commit only the three service files in the isolated branch and push that branch. Open a focused PR to `main` describing the application-only scope, credentials/bootstrap ordering, pins, local proof, and the future local-agent trust boundary. The chosen workflow requires human PR review/merge: do not self-merge or deploy the unmerged feature branch. If approval is pending, retain the local result and clearly block the deployment step on that PR; resume when merged main contains the service package.

The repository currently has no dedicated Compose-validation CI; do not present an unrelated image-build workflow as proof of this stack. The PR evidence must include the actual local syntax/runtime/auth/persistence checks.

### 5. Deploy merged main to TrueNAS and complete owner handoff

After merge, freshly resolve the Portainer environment named `truenas` and check the existing stack list. During planning it was endpoint `25`, type Edge Docker, healthy heartbeat; never assume the numeric ID remains stable. No `paperclip` stack or `/mnt/tank/container-configs/paperclip` directory existed when inspected. TrueNAS is `192.168.1.39`, accessible through SSH alias `truenas` as `truenas_admin`, Docker 28.3.1/x86_64. No observed container published host port 3100.

Confirm the merged remote `main` contains `services/paperclip/docker-compose.yml` and its documented image pins before creating a stack. Check the port and data path again. Create only these new directories, without recursive permissions changes to the parent or other applications:

- `/mnt/tank/container-configs/paperclip/app`
- `/mnt/tank/container-configs/paperclip/postgres`

After approval and the collision checks, provision only these directories with `ssh truenas 'mkdir -p /mnt/tank/container-configs/paperclip/app /mnt/tank/container-configs/paperclip/postgres'`. Read-only checks confirmed the configured SSH user can write the parent directory; noninteractive sudo requires a password and is not needed for this step. The upstream app/Postgres entrypoints own their respective empty data directories. If permissions change or inherited ACLs block ownership repair, stop for that concrete prerequisite rather than weakening the parent dataset or changing unrelated ownership.

Use fresh home-specific secrets, never the local qualification instance's secrets. Set the nonsecret Portainer values:

```dotenv
PAPERCLIP_BIND_IP=192.168.1.39
PAPERCLIP_PORT=3100
PAPERCLIP_PUBLIC_URL=http://192.168.1.39:3100
PAPERCLIP_DATA_DIR=/mnt/tank/container-configs/paperclip
PAPERCLIP_AUTH_DISABLE_SIGN_UP=false
HEARTBEAT_SCHEDULER_ENABLED=false
```

Create repository stack `paperclip` using the resolved endpoint, repository `https://github.com/mspiegel31/home-services`, ref `refs/heads/main`, and compose path `services/paperclip/docker-compose.yml`. Pass the complete variables as Portainer's `Env` array. No repository credentials are needed for this public repo. Do not request automatic polling/webhook redeployment or change the existing shared GitOps source. Do not inline/modify the deployed Compose file.

Verify the deployed Git config hash matches the merged content, both services are running/healthy, only the app publishes `192.168.1.39:3100`, and the functional/auth checks below pass. Container IDs must be resolved fresh after each redeploy.

Have the user create/claim their home owner account in the browser. Do not manufacture a permanent home account/password. After health reports `bootstrapStatus: ready`, set `PAPERCLIP_AUTH_DISABLE_SIGN_UP=true` in the stack environment and redeploy through `StackGitRedeploy` with both stack ID and endpoint ID. Preserve every other env value: send the complete retained Env array, not a partial array that discards secrets. If retained secret values are unavailable because Portainer reads redact them, have the user edit only that field in the Portainer UI and redeploy; never replace real secrets with `[REDACTED]` or regenerate them.

Create company `Home Operations`, project `Platform Validation`, and an unassigned backlog verification issue using the authenticated owner's session. They are inert application records, not agent jobs. Keep this small owner-controlled baseline for the handoff, with no agents, model credentials, GitHub connections, or scheduled jobs. Verify the home state again after a GitOps redeploy without configuration changes.

## Verification

### Local package independence and Compose validation

Prerequisites: Docker daemon running, Compose supporting `depends_on: service_healthy` and `up --wait`; browser access through the available browser tools; no model/GitHub credentials needed. Current tools: Docker client 29.7.2/ARM64 and Compose 5.4.0. Registry inspection already established both architectures for the pins.

1. Copy **only** `services/paperclip/` to a fresh temporary directory outside the repository. Generate a `.env` there with permissions 0600, an absolute sibling data root, unique disposable secrets, `PAPERCLIP_BIND_IP=127.0.0.1`, `PAPERCLIP_PORT=13100`, and `PAPERCLIP_PUBLIC_URL=http://localhost:13100`. Use project name `paperclip-local-proof`. This proves the package does not rely on repository sidecars, current checkout, `/mnt/tank`, home gateways, or external Docker networks.
2. From that copied directory:

   ```sh
   docker compose -p paperclip-local-proof --env-file .env config --quiet
   PAPERCLIP_AUTH_DISABLE_SIGN_UP=false docker compose -p paperclip-local-proof --env-file .env up -d --wait --wait-timeout 300
   curl --fail --silent --show-error http://localhost:13100/api/health
   docker compose -p paperclip-local-proof --env-file .env exec -T --user 1000:1000 paperclip opencode --version
   docker compose -p paperclip-local-proof --env-file .env exec -T db pg_isready -U paperclip -d paperclip
   ```

   Expected: two healthy services; health responds successfully and exposes pending-bootstrap state; OpenCode prints a version without needing provider authentication; Postgres accepts connections. This is harness availability, not a model compatibility test.
3. Negative interpolation check: make a temporary env input with `PAPERCLIP_POSTGRES_PASSWORD` absent/empty and clear that variable from the command environment. `docker compose ... config --quiet` must exit nonzero and identify the required password without starting containers. Repeat for empty `PAPERCLIP_DATA_DIR`. Never display a fully interpolated production config containing secrets.

### Authenticated application smoke, with zero agents

Use real browser helpers to open `http://localhost:13100`, observe the login/setup screen, create a disposable local owner account, and complete the private-install claim. Store the temporary password securely; don't show it in screenshots or chat. Verify `/api/health` reports `bootstrapStatus: ready`.

The UI onboarding flow may offer to hire a first agent. Do not submit that step. From the authenticated same-origin browser session, use `fetch` or the normal UI/API tooling for these exact operations, retaining returned IDs:

| Operation | Input | Required observation |
|---|---|---|
| `POST /api/companies` | `{"name":"Paperclip Local Proof","description":"Platform-only qualification","budgetMonthlyCents":0}` | HTTP 201, company ID returned; owner can open it |
| `POST /api/companies/{companyId}/projects` | `{"name":"Platform Validation","description":"Original description","status":"planned"}` | Project ID returned, no workspace/agent required |
| `PATCH /api/projects/{projectId}` | `{"description":"Persistence marker paperclip-local-proof"}` | Updated value returned/readable |
| `POST /api/companies/{companyId}/issues` | `{"title":"Verify platform persistence","description":"No execution requested","projectId":"<returned-project-id>","status":"backlog"}` | Unassigned backlog issue is returned and visible in the browser |
| `GET /api/companies/{companyId}/agents` | None | Empty array; no agent was seeded |

Observe the project and issue on the actual UI, and record a screenshot without account secrets. In a fresh unauthenticated browser context or unauthenticated HTTP request, protected company/project data must be denied (401/403), not returned.

Close signup by bringing the same stack up without the temporary false override:

```sh
docker compose -p paperclip-local-proof --env-file .env up -d --wait --wait-timeout 300
```

Expected: existing owner can sign in; a new signup attempt is refused; company/project/issue remain intact. No agents/routines/connections have been created. Scheduler disabled is additional restraint, not a proof that manually triggered actions would be impossible.

### Recreation, database failure, and home verification

1. Recreate both containers without removing data:

   ```sh
docker compose -p paperclip-local-proof --env-file .env up -d --force-recreate --wait --wait-timeout 300
   ```

   Sign in again if necessary; read the same company/project/issue IDs and the changed description. Signup remains closed and the agent list remains empty. Inspect the running container's process table (`docker top <resolved-container-id> -eo uid,pid,args`): the Node server must run as UID 1000. The upstream tini parent may remain UID 0; do not mistake `docker exec`'s default user or tini's identity for the server's identity.
2. On the disposable local instance only, run `docker compose -p paperclip-local-proof --env-file .env stop db`. Poll `http://localhost:13100/api/health` for up to 120 seconds: it must report failure/503 rather than healthy database readiness. Recover with `docker compose -p paperclip-local-proof --env-file .env up -d --wait --wait-timeout 300`, then read the same records. Do not perform this fault injection against other home stacks or delete data to recover.
3. On TrueNAS, repeat owner claim, blank-company/project/backlog-issue creation, signup closure, unauthenticated denial, and persistence after `StackGitRedeploy`. Use home URL `http://192.168.1.39:3100`; company is `Home Operations`. Do not reuse the local disposable owner or secrets. Observe the UI remotely rather than declaring success from Portainer `running` status alone.
4. Handoff evidence: merged PR/commit; stack name/ID and freshly resolved environment; image pins; observed UI URL; health/bootstrap status; signup closed; persisted object IDs; zero agents; and separate local ARM64 versus home AMD64 observations. Explicitly state that no model run, GitHub integration, unattended operation, OIDC, or hardened agent sandbox was exercised.

The local qualification instance is a disposable test fixture. After all its recreation/failure/readback checks and evidence capture, stop it from the copied service directory with `docker compose -p paperclip-local-proof --env-file .env down` (no `-v`). Never apply that fixture teardown to the TrueNAS installation.

## Assumptions and contingencies

- **Scope and authority:** platform-only, OpenCode first, one owner, agents unconfigured, HTTP confined to trusted LAN/VPN. Later unattended jobs require separately authorized targets/actions and credentials. Changing any of those requirements changes the plan; don't silently add a proxy, custom worker, OMP integration, or operational agent.
- **PR gate:** human review/merge is required before TrueNAS deployment. If pending, the implementation is blocked specifically on that PR; local qualification is not home-deployment completion. No direct push to main or feature-branch deployment substitutes for the selected workflow.
- **Bootstrap gate:** the user enters the permanent owner account credentials during a supervised bootstrap window. If they cannot complete the claim, stop only the new Paperclip stack while preserving its data and env; resume it with the temporary open-signup setting when the user is ready. Do not leave an unclaimed installation with open signup running indefinitely, and do not claim application acceptance. Never publish a claim URL or disable application auth to bypass the gate.
- **Existing state/collisions:** if a `paperclip` stack, nonempty target data directory, or occupied desired port appears before execution, do not overwrite or repurpose it. Inspect ownership/configuration; if it isn't this plan's installation, stop for a specific collision decision. A local qualification-port collision may use 13101, updating both `PAPERCLIP_PORT` and the canonical URL; if that is also occupied, obtain a free loopback port and record it before starting.
- **Local runtime unavailable:** start the installed Docker Desktop during approved execution. If it cannot become operational, finish reachable source work but block runtime qualification/PR readiness on that prerequisite; don't claim portability from manifest inspection or TrueNAS alone.
- **Startup failure:** diagnose the new stack's logs, mount ownership, database health, and tagged upstream contract. Preserve mounted data and keys. Fix the repository package and re-qualify; do not hot-edit the running Compose definition, switch to embedded Postgres, use `latest`, grant privileged mode, or mount the Docker socket as a fallback.
- **Portainer reachability:** Edge heartbeat alone does not prove its command tunnel. If read/deploy commands cannot reach TrueNAS, finish reachable repository/local work and block the home step on restoring the existing tunnel. Do not rotate/recreate the Portainer agent as part of this application plan.
