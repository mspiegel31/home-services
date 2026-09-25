---
name: omni-management-stack
description: Bring up, update, and operate the outside-cluster management Compose stack (Omni, Omni-only Pocket ID, stock-Traefik reverse proxy, Uptime Kuma, opt-in Proxmox infra provider, git-sync config sidecar) deployed as a Portainer repository stack on the management VM. Use when the user asks to deploy, stage, debug, redeploy, or back up the management stack, set its Portainer variables, enable the Proxmox provider, or change the Traefik route config. Don't use for Proxmox cluster formation from standalone hosts (see omni-proxmox-cluster), household Pocket ID, or in-cluster Kubernetes work.
---

# Management Stack

Deploy and operate the outside-cluster management Compose stack (home-prod
plan §5) from `services/omni/docker-compose.yml` in this repository:
self-hosted Omni, the Omni-only Pocket ID instance, the official Proxmox
infrastructure provider, a stock-Traefik management reverse proxy, and the
outside-cluster availability monitor. It runs on a dedicated general-purpose
VM on the management host and is the first service group of the migration.

Bootstrap inputs (DNS helper, DNS record allowlist, Omni config example)
live in `home-prod/bootstrap/management/`; the full deployment/operations
procedure lives in `home-prod/docs/management-stack.md`.

**Hard rules:**
- A plain `docker compose up -d` **never** starts the Proxmox provider.
  Only `docker compose --profile provider up -d omni-infra-provider-proxmox`
  does. Initial bring-up must not mutate Proxmox.
- Endpoints are LAN/VPN-only. Management-host downtime is accepted and must
  not stop household identity or existing Kubernetes workloads.
- Secrets never enter this repository. Only the non-secret proxy config
  (`traefik/dynamic.yaml`) is tracked; everything else is operator-protected
  on the management host.

## Stack

| Service | Image | Role |
|---|---|---|
| `omni` | `ghcr.io/siderolabs/omni:v1.12.2` | Node lifecycle + cluster management; embedded etcd, OIDC to Pocket ID, break-glass enabled |
| `pocket-id` | `ghcr.io/pocket-id/pocket-id:2.16.0` | Omni-only identity; separate issuer/DB/keys/clients from the household instance |
| `traefik` | `traefik:v3.7.6` (pinned digest) | Management HTTPS; public DNS-01 via the Cloudflare provider bundled in the stock image (scoped token) |
| `uptime-kuma` | `ghcr.io/louislam/uptime-kuma:2.5.5` | Outside-cluster availability monitor, SMTP notifications via UI config |
| `omni-infra-provider-proxmox` | `ghcr.io/siderolabs/omni-infra-provider-proxmox:v0.3.0` | Proxmox VM provisioning; **opt-in profile, disabled by default** |
| `git-sync` | `registry.k8s.io/git-sync/git-sync:v4.4.2` (pinned digest) | Places the non-secret proxy config (`traefik/dynamic.yaml`) on the server for the Portainer stack; anonymous HTTPS (public repo) |

## Topology

Loopback-minimal; no private API is bound to `0.0.0.0` except the
plan-mandated machine API. External LAN/VPN exposure is exactly
`443/tcp` (Traefik TLS), `8090/tcp` (Omni machine API) and
`50180/udp` (SideroLink WireGuard).

- **Traefik** — host network; binds `${MGMT_LAN_IP}:443` (TLS, DNS-01).
  The only listener. File provider only: no Docker socket, no labels
  provider, no dashboard. All static config is passed as CLI flags; the
  only file is the dynamic route config `traefik/dynamic.yaml`, a native
  Go template the file provider renders from `{{ env "..." }}` at load
  time (no entrypoint script). It is placed on the server by the
  `git-sync` sidecar.
- **Omni** — host network; listeners set in the reviewed
  `omni-config.yaml`: API `127.0.0.1:8443` (cleartext h2c), k8s-proxy
  `127.0.0.1:8095` (TLS, internal CA), machine API `0.0.0.0:8090`
  (LAN/VPN direct from Talos nodes).
- **Pocket ID / Uptime Kuma** — bridge network, published to host loopback
  only (`127.0.0.1:1411`, `127.0.0.1:3001`); Traefik reaches them via
  `127.0.0.1`.
- **Provider** — host network (opt-in profile) so it reaches the loopback
  Omni API; `OMNI_ENDPOINT` is the fixed loopback path for the same-VM
  internal use. External clients still use HTTPS.

Routes (single `:443` listener, one hostname each):

| Hostname | Upstream |
|---|---|
| `omni.<MGMT_DOMAIN>` | `h2c://127.0.0.1:8443` (gRPC-capable) |
| `omni-k8s.<MGMT_DOMAIN>` | `https://127.0.0.1:8095` (internal CA trusted, SNI pinned) |
| `pocket-id.<MGMT_DOMAIN>` | `http://127.0.0.1:1411` |
| `monitor.<MGMT_DOMAIN>` | `http://127.0.0.1:3001` |
| anything else | Traefik default 404 (no catch-all router) |

## Bring-up order

1. Create the host directories and one-time secrets on the VM (see
   `home-prod/docs/management-stack.md` for the exact procedure):
   `/opt/omni-mgmt/omni`, `/opt/omni-mgmt/omni-config` (config + `omni.asc`
   + internal TLS), `/opt/omni-mgmt/pocket-id` (state),
   `/opt/omni-mgmt/pocket-id-key` (`encryption.key`),
   `/opt/omni-mgmt/omni-k8s-ca/ca.crt`, `/opt/omni-mgmt/provider`
   (provider `config.yaml`), `/opt/omni-mgmt/pve-ca-bundle.pem`.
2. Run the management DNS helper (home-prod
   `bootstrap/management/dns.py`) from the workstation: preview, then apply
   the local UniFi A records for the four management hostnames.
3. Stage the dependencies **before** Omni, so Omni finds a running issuer
   and proxy on first start (no restart loop):
   ```sh
   docker compose up -d pocket-id traefik uptime-kuma
   ```
   Then create the operator user and the Omni OIDC client in Pocket ID
   (`/setup`), complete `omni-config.yaml` (client ID/secret, account UUID,
   etcd GPG key), and start Omni:
   ```sh
   docker compose up -d omni
   ```
4. Verify HTTPS on all four hostnames (DNS-01 certs are issued by Traefik)
   and the Omni login flow.

## Provider enablement gate

The Proxmox provider starts **only** with an explicit opt-in:

```sh
docker compose --profile provider up -d omni-infra-provider-proxmox
```

Before enabling, complete the Proxmox cluster prerequisites (the
`omni-proxmox-cluster` skill) and create the least-privilege Proxmox
token; PVE-version-dependent ACL verification is an operator gate, not an
assumed least privilege. The provider connects with verified TLS: mount
the Proxmox API CA as `pve-ca-bundle.pem` (`SSL_CERT_FILE`); the bundle
must retain the public roots plus the PVE CA; do not use
`insecureSkipVerify`.

## Portainer variables (UI, no env_file)

| Variable | Used by | Notes |
|---|---|---|
| `TZ` | all | time zone |
| `MGMT_LAN_IP` | traefik | management VM LAN/VPN address the `:443` listener binds to (default 127.0.0.1) |
| `ACME_EMAIL` | traefik | ACME account email for DNS-01 |
| `CF_DNS_API_TOKEN` | traefik | scoped Cloudflare zone:edit DNS token for private DNS-01; lego official name; provisioned outside ESO |
| `OMNI_CONFIG_REF` | git-sync | config ref to sync; default `main` post-merge, branch or immutable SHA pre-merge; must match the Portainer stack ref |
| `OMNI_HOSTNAME` | traefik | e.g. `omni.<mgmt-domain>` |
| `OMNI_K8S_HOSTNAME` | traefik | e.g. `omni-k8s.<mgmt-domain>` |
| `POCKET_ID_APP_URL` | pocket-id | issuer URL, e.g. `https://pocket-id.<mgmt-domain>` |
| `OMNI_STATE_DIR`, `OMNI_CONFIG_DIR` | omni | host paths for durable state and reviewed config |
| `SMTP_HOST`/`SMTP_PORT`/`SMTP_FROM`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_TLS` | pocket-id | recovery/verification email; empty leaves defaults |
| `POCKET_ID_STATE_DIR`, `POCKET_ID_KEY_DIR` | pocket-id | host paths for state and encryption key |
| `OMNI_K8S_CA` | traefik | host path to the internal CA for the Traefik→Omni k8s-proxy hop |
| `PROVIDER_KEY` | provider | infra provider key; injected via env, never argv |
| `PROVIDER_CONFIG_DIR` | provider | host path to the provider `config.yaml` (Proxmox token) |
| `PVE_CA_BUNDLE` | provider | host path to the Proxmox API CA bundle (public roots + PVE CA) |

The provider's `OMNI_ENDPOINT` is the fixed loopback `http://127.0.0.1:8443`
(same-VM internal path); it is not a UI variable.

Uptime Kuma monitors, SMTP notification and email alerts are configured in
its UI (the pinned release does not read `SMTP_*` environment variables);
the monitor set is documented in home-prod `docs/management-stack.md`.

## Config placement (git-sync sidecar)

Portainer CE deploys a repository stack from the server-side image; it does
not read this repository's relative `./traefik/dynamic.yaml` bind. The
`git-sync` sidecar places the non-secret proxy config on the server so the
stack is self-contained:

- Image: `registry.k8s.io/git-sync/git-sync:v4.4.2` (pinned digest), the
  same named-volume pattern as the litellm stack. The repository is
  public, so it pulls over anonymous HTTPS — no token.
- Named volume `omni-config:/git` (Docker-managed, not a host bind);
  `user: "0:0"` because the volume is Docker-owned. Sparse checkout of
  `services/omni/`; `--root=/git`, `--link=current`, `--depth=1`,
  `--period=30s`.
- Traefik mounts `omni-config:/config:ro` and reads
  `/config/current/services/omni/traefik/dynamic.yaml`.
- The config ref must match the Portainer stack ref: default `main`
  post-merge; use a branch or immutable SHA via `OMNI_CONFIG_REF`
  pre-merge.
- `--providers.file.watch=false` is deliberate: after a sync, restart or
  redeploy the stack to pick up the new route config (no assumed
  symlink-watch).

**Separation of secrets from config:** the operator-protected host files —
Omni `omni-config.yaml` + `omni.asc`, the provider `config.yaml`, and every
secret (Pocket ID key, internal CA, PVE CA bundle, all `${VAR}` values) —
stay on the management host and are never checked in. Only the non-secret
proxy config travels through git-sync.

## Pocket ID state and key ownership

The Pocket ID image runs as UID/GID **1000** (official image default
`PUID`/`PGID`). The state and key directories are created on the host with
`umask 077` by root, which makes them unreadable to the container unless
ownership is set explicitly. On first setup:

```sh
chown -R 1000:1000 /opt/omni-mgmt/pocket-id /opt/omni-mgmt/pocket-id-key
```

Restrict ownership to the image UID (`1000:1000`, or an explicitly verified
image UID if the image changes). Do **not** use `chmod 777` or any general
unprotected permission. The `encryption.key` file and the SQLite state
remain readable only by the container user and root.

## Backups and recovery

Native consistent exports (Omni etcd/datastore, Pocket ID database, monitor
state), encrypted before off-site upload, are specified in
`home-prod/docs/management-stack.md`. A live embedded etcd directory copy
is not a consistent backup. Break-glass material (account UUID, etcd GPG
key, datastore recovery) is stored independently of the managed cluster.
