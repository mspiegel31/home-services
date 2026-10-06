---
name: omni-management-stack
description: Edit-time facts for the outside-cluster management Compose stack (Omni, Omni-only Pocket ID, stock-Traefik reverse proxy, opt-in Proxmox infra provider, git-sync config sidecar) deployed as a Portainer CE edge stack on the TrueNAS SCALE host. Browser-facing endpoints use public hostnames under one management subzone with Let's Encrypt DNS-01 via Cloudflare. Use when changing services/omni/ in this repository — compose, Traefik route config, Portainer variables — or when the user asks about the stack's layout. Deployment/operations procedure lives in home-prod/docs/management-stack.md; don't use for Proxmox cluster formation (see omni-proxmox-cluster), household Pocket ID, or in-cluster Kubernetes work.
---

# Management Stack

Edit-time facts for `services/omni/` in this repository: the outside-cluster
management stack (home-prod plan §5) running on the **TrueNAS SCALE host**
(`192.168.1.39`, bare-metal Docker) as a **Portainer CE edge stack** on
the `truenas` environment. Ownership: the home-prod plan §5 owns
requirements; `home-prod/docs/management-stack.md` owns the procedure;
this skill holds only what you need while editing these files.

**Procedure — see `home-prod/docs/management-stack.md`:**
- Architecture / rationale for public hostnames → Architecture
- Cloudflare token, DNS records → Cloudflare token and DNS
- Host prep script → Host prep
- Edge-stack creation and variables → Create the edge stack
- First bring-up → Bring-up order
- Post-deploy checks → Verification
- Failure modes → Known traps
- Enabling the Proxmox provider → Provider enablement gate
- Backup set → Backups and recovery
- Old IP-only deployment → Relationship to the retired IP-only deployment

**Hard rules:**
- A plain deployment **never** starts the Proxmox provider. Only the
  `provider` profile does. Initial bring-up must not mutate Proxmox.
- Endpoints are LAN/VPN-only. Management-host downtime is accepted and must
  not stop household identity or existing Kubernetes workloads.
- Secrets never enter this repository. Only the non-secret proxy config
  (`traefik/dynamic.yaml`) is tracked; everything else is operator-protected
  on the host.

## Stack

| Service | Image | Role |
|---|---|---|
| `omni` | `ghcr.io/siderolabs/omni:v1.12.2` | Node lifecycle + cluster management; embedded etcd, OIDC to Pocket ID, break-glass enabled |
| `pocket-id` | `ghcr.io/pocket-id/pocket-id:v2.16.0` | Omni-only identity; separate issuer/DB/key/clients from any household instance |
| `traefik` | `traefik:v3.7.6` (pinned digest) | Management HTTPS; wildcard certificate via public DNS-01 using the Cloudflare provider bundled in the stock image |
| `omni-infra-provider-proxmox` | `ghcr.io/siderolabs/omni-infra-provider-proxmox:v0.3.0` | Proxmox VM provisioning; **opt-in profile, disabled by default** |
| `git-sync` | `registry.k8s.io/git-sync/git-sync:v4.4.2` (pinned digest) | Delivers the non-secret proxy config (`traefik/dynamic.yaml`) into a shared volume; anonymous HTTPS (public repo) |

## Listeners and routes

Single LAN-facing listener `192.168.1.39:9443` (TrueNAS owns 80/443);
Host-header routing, no per-service host ports. Omni's machine API
(`192.168.1.39:8090`) and SideroLink (`50180/udp`) are the other
LAN-facing endpoints; the machine API must bind the specific LAN IPv4,
never `0.0.0.0` (dual-stack IPv6 wildcard collides with the SideroLink
event sink on port 8090). Everything else is loopback-only.

| Route (Traefik → upstream) | |
|---|---|
| `omni.<MGMT_DOMAIN>` | `h2c://127.0.0.1:8443` (gRPC-capable) |
| `omni-k8s.<MGMT_DOMAIN>` | `https://127.0.0.1:8095` (self-signed; `insecureSkipVerify` — loopback-only hop) |
| `pocket-id.<MGMT_DOMAIN>` | `http://127.0.0.1:1411` |
| anything else | Traefik default 404 (no catch-all router) |

## Portainer variables (UI, no env_file)

Only `TZ`, `ACME_EMAIL`, `CF_DNS_API_TOKEN` and `MGMT_DOMAIN` are required
(fail-fast `${VAR:?…}` form). `OMNI_CONFIG_REF` is optional (see git-sync
below). The hostnames default to their well-known labels under
`MGMT_DOMAIN` (`omni.`, `omni-k8s.`, `pocket-id.`), `POCKET_ID_URL`
defaults to `https://pocket-id.<MGMT_DOMAIN>:9443`, and `PUID`/`PGID`
default to `1000` — override only for a non-default layout.

| Variable | Used by | Notes |
|---|---|---|
| `TZ` | all | time zone |
| `ACME_EMAIL` | traefik | ACME account email for DNS-01 |
| `CF_DNS_API_TOKEN` | traefik | scoped Cloudflare token, **Zone:DNS:Edit for the management zone only** — never a Global API Key |
| `MGMT_DOMAIN` | traefik | the management subzone, e.g. `mgmt.example.net`; the wildcard and all hostnames derive from it |
| `OMNI_CONFIG_REF` | git-sync | optional pin of the config branch/SHA; case-sensitive; must equal the edge stack's Reference; defaults to `main` |
| `PROVIDER_KEY` | provider | infra provider key; injected via env, never argv (provider profile only); deliberately `${PROVIDER_KEY:-}` — compose interpolates all services regardless of profile, so fail-fast here would break plain deploys |

Host paths and the listener address are hardcoded in the compose, matching
the other stacks on this host (`/mnt/tank/container-configs/omni-mgmt/...`,
`192.168.1.39:9443`). The provider's `OMNI_ENDPOINT` is the fixed loopback
`http://127.0.0.1:8443` and is not a UI variable.

## Traefik dynamic config traps (`traefik/dynamic.yaml`)

- **Wildcard-only rule:** every router's `tls.domains` is exactly one
  entry, `main: '*.<MGMT_DOMAIN>'`, no `sans` — one DNS-01 order reused
  for all SNI names. Never add the subzone apex (TXT-record race; see docs
  → Known traps). No hostname uses the apex.
- **Quoting trap 1:** the file must be valid YAML *including* the
  placeholder text, so the wildcard entry is single-quoted. Unquoted, `{{`
  parses as a flow mapping and `*` as an alias.
- **Quoting trap 2:** never put quotes inside the templated value —
  Traefik parses the YAML first and templates the resulting *value*, so
  injected quotes land in the domain string and ACME orders `"*...."`.
  Verify via the Traefik API (`/api/http/routers`) that `main` reads
  `*.mgmt.example.net`, not `"*.mgmt.example.net"`.

## Config placement (git-sync sidecar)

Portainer CE drops compose `configs:` and does not resolve relative
bind-mount paths, so the proxy config cannot ride in the stack definition
— the sidecar is **required by the platform**, not a preference.

- `--ref=${OMNI_CONFIG_REF:-main}`: set only to pin a branch/SHA;
  case-sensitive (a typo like `MAIN` fails the sync). Must equal the edge
  stack's Reference.
- No sparse-checkout file: the upstream design passed one through compose
  `configs:`, which Portainer drops; this variant takes a full `--depth=1`
  checkout instead of adding an init container.
- Traefik mounts the same volume read-only and reads
  `/config/current/services/omni/traefik/dynamic.yaml`.
- `--providers.file.watch=false` is deliberate: after a sync, **restart or
  redeploy Traefik** to apply a route change.
- The sidecar's healthcheck asserts the route file exists (the file
  provider loads it once at startup, so a missing file means no routes at
  all) and that its HTTP endpoint answers; Traefik depends on that health.
- Only the non-secret proxy config travels through git-sync; all
  operator-protected files (Omni config + keys, provider config, Pocket ID
  encryption key, CA bundle) stay on the host.

## Pocket ID (v2.x)

v2 renamed the v0.53.x env names — do not copy environment from the older
IP-only stack:

| v2.x | v0.53.x |
|---|---|
| `APP_URL` | `PUBLIC_APP_URL` |
| `UI_CONFIG_DISABLED` | `PUBLIC_UI_CONFIG_DISABLED` |

Image contract verified against v2.16.0 source and image: entrypoint
`/app/docker/entrypoint.sh`, binary `/app/pocket-id`, state `/app/data`
(chowned to `PUID`/`PGID` by the entrypoint), port `1411/tcp`, and the
image supplies its own healthcheck (no override needed).
`ENCRYPTION_KEY_FILE` must contain **at least 16 bytes**
(`openssl rand -base64 32`). State and key directories are owned by the
container user; do **not** use `chmod 777`. The tag is `v2.16.0` **with
the `v`** — `2.16.0` does not exist and fails as `manifest unknown`.

## Decisions to keep (don't re-litigate)

- The `omni-k8s` route and its self-signed k8s-proxy certificate are
  pre-provisioned for the first cluster's kubeconfig even though no
  cluster exists yet.
- The `provider` profile costs nothing while off; leaving it in the
  compose is deliberate.
- git-sync is required by Portainer CE (see above), not legacy.
- Passkeys are bound to the RP ID: changing the issuer hostname
  invalidates existing passkeys, and
  `POST /api/one-time-access-token/setup` only works while the initial
  admin has no WebAuthn credential.
