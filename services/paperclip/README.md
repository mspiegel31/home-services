# Paperclip — portable home platform

Self-contained Paperclip application + PostgreSQL for a trusted-LAN/VPN or
local install. This package is the **application platform only**:
authenticated ownership, company/project/issue CRUD, and persistent state.
OpenCode is present in the image, but no agents, model credentials, GitHub
credentials, scheduled agent jobs, or operations permissions are configured
by this stack.

## Images and requirements

| Service | Image | Architectures | Limits |
|---|---|---|---|
| `paperclip` | `ghcr.io/paperclipai/paperclip:2026.916.1@sha256:a02ac35ac41df911af477422ea0e781cf41d2b2c600c66f0a5ac9d8c63f52c2c` | linux/amd64, linux/arm64 | 4G RAM, 2.0 CPUs |
| `db` | `postgres:17.10-alpine@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193` | linux/amd64, linux/arm64 | 1G RAM, 1.0 CPU |

- No `platform:` override is set, so the stack runs natively on amd64
  (TrueNAS) and arm64 (Apple Silicon) hosts.
- Required Docker Compose features: `depends_on: condition: service_healthy`
  and `up --wait` (Compose v2.1+).
- The app image ships OpenCode, `curl`, `git`, and GitHub CLI. Its upstream
  tini/entrypoint repairs initial volume ownership as root, then runs the
  application as `node` (UID/GID 1000). Do not add `init: true`, override the
  entrypoint, force `user:`, or drop capabilities — the ownership transition
  depends on them.
- No Portainer, home DNS, tunnel, shared gateway, or home-services Git access
  is needed to run a copied folder locally; only registry access is needed to
  pull the images initially.
- Network shape: `paperclip` sits on an ordinary bridge (`application`) plus
  an internal `database` network; `db` sits only on `database` and publishes
  no host ports. Networks are stack-scoped (no global names) and no
  `container_name` is set, so a second installation can use a different
  Compose project name without collisions.

## Scope and security boundary

- **HTTP only**, accepted solely on a trusted LAN/VPN. No TLS, reverse proxy,
  or OIDC layer is added by this stack; `TRUST_PROXY` is intentionally unset.
- One owner account; sign-up is closed after bootstrap
  (`PAPERCLIP_AUTH_DISABLE_SIGN_UP=true`).
- **No configured agents, connections, or secrets for operations.**
  `HEARTBEAT_SCHEDULER_ENABLED=false` disables timers, not every API-driven
  wake; zero agents and absent credentials are the primary dormant posture.
- The app container holds its own database credentials, so this split is not
  a sandbox boundary for later local agents. Any agent that runs inside the
  app container (e.g. OpenCode invoked locally) would share the app's full
  authority. Later agents require a separate decision about secrets,
  execution isolation, and target/action allowlists.
- **Loopback port constraint:** at startup the application rewrites a
  loopback (`localhost`/`127.0.0.1`) `PAPERCLIP_PUBLIC_URL` port to its
  internal listen port (3100). A local install that publishes a *different*
  host port therefore has a mismatched trusted origin and cannot complete
  browser sign-up. Use host port 3100 for loopback installs (the default),
  or a non-loopback canonical URL for LAN installs such as TrueNAS.

## Configuration

Create a `.env` next to `docker-compose.yml` (git-ignored) and fill in every
required value:

```dotenv
# five independent secrets — openssl rand -hex 32 each
PAPERCLIP_POSTGRES_PASSWORD=
BETTER_AUTH_SECRET=
PAPERCLIP_AGENT_JWT_SECRET=
PAPERCLIP_TOOL_ACTION_SIGNING_SECRET=
PAPERCLIP_SECRETS_MASTER_KEY=
# nonsecret values
PAPERCLIP_DATA_DIR=
PAPERCLIP_BIND_IP=127.0.0.1
PAPERCLIP_PORT=3100
PAPERCLIP_PUBLIC_URL=http://localhost:3100
PAPERCLIP_AUTH_DISABLE_SIGN_UP=true
HEARTBEAT_SCHEDULER_ENABLED=false
```

```sh
chmod 600 .env
```

The root `.gitignore` already protects `.env`; this file must never receive
generated credentials. **Shell environment variables override `.env`** — when
switching between installations on the same machine, unset exported variables
that would shadow the intended values.

### Required secrets (five independent values)

Generate each independently with `openssl rand -hex 32`. Never reuse a value
across installations, and never write real values into chat, screenshots, or
version control.

| Key | Notes |
|---|---|
| `PAPERCLIP_POSTGRES_PASSWORD` | URL-safe hex; used by `db` and in the app's `DATABASE_URL` |
| `BETTER_AUTH_SECRET` | Persistent authentication secret |
| `PAPERCLIP_AGENT_JWT_SECRET` | Persistent agent signing secret |
| `PAPERCLIP_TOOL_ACTION_SIGNING_SECRET` | Persistent tool-action signing secret |
| `PAPERCLIP_SECRETS_MASTER_KEY` | 32 bytes as 64 hex characters; encrypts stored secrets |

Regenerating any of these on an existing installation breaks sign-in,
signatures, or secret decryption — preserve them across upgrades and
recreation.

### Nonsecret values

| Key | Default | Notes |
|---|---|---|
| `PAPERCLIP_DATA_DIR` | *(required, blank in template)* | Absolute writable path **outside the checkout**; holds `app/` and `postgres/`. Work/local: `$HOME/.local/share/paperclip` (expand `$HOME` when writing it). TrueNAS: `/mnt/tank/container-configs/paperclip`. |
| `PAPERCLIP_BIND_IP` | `127.0.0.1` | Host interface for the app port; use a LAN address for trusted-LAN installs. |
| `PAPERCLIP_PORT` | `3100` | Host port (container port is 3100). |
| `PAPERCLIP_PUBLIC_URL` | `http://localhost:3100` | Canonical URL including scheme and port; the accepted hostname. |
| `PAPERCLIP_AUTH_DISABLE_SIGN_UP` | `true` | Keep `true` except during the initial bootstrap override below. |
| `HEARTBEAT_SCHEDULER_ENABLED` | `false` | Application timers; keep disabled for the platform-only posture. |

Blank required values fail Compose interpolation before any container
starts. `PAPERCLIP_MANAGED_CONFIG` is intentionally never set (an empty
variable is not an acceptable substitute), and baked-in `HOST`, `PORT`,
`HOME`, `PAPERCLIP_HOME`, `PAPERCLIP_CONFIG`, and `SERVE_UI` are left
unchanged.

## Local install (work/home workstation)

From `services/paperclip/` with a filled `.env`:

```sh
docker compose --env-file .env config --quiet
PAPERCLIP_AUTH_DISABLE_SIGN_UP=false docker compose --env-file .env up -d --wait --wait-timeout 300
# Create/claim the first owner through the browser before the next command.
docker compose --env-file .env up -d --wait --wait-timeout 300
```

`.env` retains `PAPERCLIP_AUTH_DISABLE_SIGN_UP=true`; the inline `false`
override exists only for first bootstrap. Do not run the open-signup command
against an already claimed installation during routine upgrades.

1. Open the canonical URL (`http://localhost:3100` by default).
2. Create one owner account in the browser, then use the documented
   private-install **Claim this instance** action (or the one-time
   board-claim URL in the startup output, if this release displays one).
   Claim URLs and passwords are sensitive — never paste them in PRs or chat.
   The owner chooses their own email/password; nothing is hardcoded in
   Compose.
3. Verify `curl --fail http://localhost:3100/api/health` flips from
   `bootstrap_pending` to `ready`.
4. The stack is then running with sign-up closed (the second `up` in the
   block above).
5. Create a blank company and project **without** completing the UI's
   hire-an-agent/model wizard — a blank company seeds no CEO/built-in agent
   in this release, and no model is needed to dismiss onboarding.

### Shutdown and recreation

```sh
docker compose --env-file .env stop          # data preserved
docker compose --env-file .env up -d --wait --wait-timeout 300
docker compose --env-file .env up -d --force-recreate --wait --wait-timeout 300
```

- Mounted data survives all of the above. **Never use volume/data deletion as
  a troubleshooting step**, and never `down -v`.
- Preserve the five signing/encryption/database secrets on every upgrade and
  recreation.
- Changing `PAPERCLIP_POSTGRES_PASSWORD` in env does **not** rotate the
  password in an existing PostgreSQL data directory; the database keeps its
  original credentials.

## TrueNAS install (GitOps through Portainer CE)

Create only these directories (no recursive permission changes to the
parent):

```sh
ssh truenas 'mkdir -p /mnt/tank/container-configs/paperclip/app /mnt/tank/container-configs/paperclip/postgres'
```

The upstream app/Postgres entrypoints own their respective empty data
directories. If inherited ACLs block ownership repair, stop and fix that
specific prerequisite rather than weakening the parent dataset.

Portainer stack `paperclip` on the `truenas` environment, repository
`https://github.com/mspiegel31/home-services`, ref `refs/heads/main`, compose
path `services/paperclip/docker-compose.yml`, with this `Env` array
(secrets freshly generated per the table above — never copied from a local
qualification instance):

```dotenv
PAPERCLIP_BIND_IP=192.168.1.39
PAPERCLIP_PORT=3100
PAPERCLIP_PUBLIC_URL=http://192.168.1.39:3100
PAPERCLIP_DATA_DIR=/mnt/tank/container-configs/paperclip
PAPERCLIP_AUTH_DISABLE_SIGN_UP=false
HEARTBEAT_SCHEDULER_ENABLED=false
# plus the five required secrets
```

Owner-bootstrap sequence:

1. Deploy with `PAPERCLIP_AUTH_DISABLE_SIGN_UP=false` (bootstrap window).
2. The owner creates/claims their home account in the browser at
   `http://192.168.1.39:3100`; health must report `bootstrapStatus: ready`.
3. Set `PAPERCLIP_AUTH_DISABLE_SIGN_UP=true` in the stack environment and
   redeploy (e.g. `StackGitRedeploy`), sending the **complete** retained
   `Env` array — never a partial one that discards secrets. If Portainer
   read responses redact retained secret values, the user edits only that
   field in the Portainer UI and redeploys; never replace real secrets with
   `[REDACTED]` or regenerate them.
4. Create the baseline records with the authenticated owner session: company
   `Home Operations`, project `Platform Validation`, one unassigned backlog
   issue. These are inert application records, not agent jobs.
5. Verify state again after a GitOps redeploy without configuration changes.

## Work-local reconfiguration

To move the install to a different machine, change only: the data root
(`PAPERCLIP_DATA_DIR`), bind address/port, canonical URL, and the five
secrets (copy them from the old `.env` to keep auth/state intact). GitHub and
model setup are not required to boot or pass platform acceptance, and
provisioning a GitHub App alone does **not** make the self-hosted agent
connector work.
