---
name: omni-management-stack
description: Bring up, update, and operate the outside-cluster management Compose stack (Omni, Omni-only Pocket ID, stock-Traefik management reverse proxy, Uptime Kuma, opt-in Proxmox infra provider) deployed as a Portainer repository stack on the management VM (192.168.1.51). IP-only, self-signed design: four dedicated Traefik entrypoint ports, one IP-SAN cert, no DNS. Use when the user asks to deploy, stage, debug, redeploy, or back up the management stack, set its Portainer variables, enable the Proxmox provider, or change the Traefik route config. Don't use for Proxmox cluster formation from standalone hosts (see omni-proxmox-cluster), household Pocket ID, or in-cluster Kubernetes work.
---

# Management Stack

Deploy and operate the outside-cluster management Compose stack (home-prod
plan §5, IP-only/self-signed variant) from
`services/omni/docker-compose.yml` in this repository: self-hosted Omni, the
Omni-only Pocket ID instance, the official Proxmox infrastructure provider,
a stock-Traefik management reverse proxy, and the outside-cluster
availability monitor. It runs on a dedicated general-purpose VM
(`cloud@192.168.1.51`) and is the first service group of the migration.

Bootstrap inputs (omni-config example, DNS helper) live in
`home-prod/bootstrap/management/`; the full deployment/operations procedure
lives in `home-prod/docs/management-stack.md`.

**Hard rules:**
- A plain `docker compose up -d` **never** starts the Proxmox provider.
  Only `docker compose --profile provider up -d omni-infra-provider-proxmox`
  does. Initial bring-up must not mutate Proxmox.
- Endpoints are LAN/VPN-only, reached by **IP on dedicated ports** — no DNS
  names, no DNS-01. Management-host downtime is accepted and must not stop
  household identity or existing Kubernetes workloads.
- Secrets never enter this repository. Only the compose file is tracked;
  every cert, key, and `omni-config.yaml` is operator-protected on the
  management host.

## IP-only design (deviation from plan §5)

Plan §5 called for management hostnames + DNS-01 certs via local
UniFi/Cloudflare DNS. The operator has no local DNS and chose IP-only as
the final design:

- Each service gets its **own dedicated Traefik entrypoint port** (the Omni
  API is gRPC, so path-based routing on one port is not an option):

| Port | Service | Upstream |
|---|---|---|
| `9444/tcp` | Omni (UI + gRPC API) | `h2c://127.0.0.1:8443` (cleartext h2c) |
| `9095/tcp` | Omni k8s-proxy | `https://127.0.0.1:8095` (internal CA, IP SAN) |
| `9411/tcp` | Pocket ID (Omni-only issuer) | `http://127.0.0.1:80` (internal Caddy) |
| `9001/tcp` | Uptime Kuma (monitor) | `http://127.0.0.1:3001` |
| `8090/tcp` | Omni machine API (direct, not proxied) | Talos nodes → `0.0.0.0:8090` |
| `50180/udp` | SideroLink WireGuard (direct) | — |

- One **IP-SAN self-signed cert** (mgmt CA) serves all four entrypoints
  via the Traefik v3 **default store** (`tls.stores.default.defaultCertificate`
  in the dynamic file — the no-SNI/IP fallback). Browsers show cert warnings;
  that is accepted.
- **No git-sync sidecar**: the route config is static (no hostnames to
  template), so it is a host bind mount, not a sidecar.
- **No `traefik-acme` volume, no `ACME_EMAIL`, no `CF_DNS_API_TOKEN`, no
  hostname variables.**

## Stack

| Service | Image | Role |
|---|---|---|
| `omni` | `ghcr.io/siderolabs/omni:v1.12.2` | Node lifecycle + cluster management; embedded etcd, OIDC to Pocket ID, break-glass enabled |
| `pocket-id` | `ghcr.io/pocket-id/pocket-id:v0.53.0` | Omni-only identity; separate issuer/DB/keys/clients from the household instance |
| `traefik` | `traefik:v3.7.6` (pinned digest) | Management HTTPS on four dedicated entrypoints; IP-SAN self-signed cert; file provider only (no Docker socket, no labels provider, no dashboard) |
| `uptime-kuma` | `ghcr.io/louislam/uptime-kuma:2.5.5` | Outside-cluster availability monitor, SMTP notifications via UI config |
| `omni-infra-provider-proxmox` | `ghcr.io/siderolabs/omni-infra-provider-proxmox:v0.3.0` | Proxmox VM provisioning; **opt-in profile, disabled by default** |

## Topology

Loopback-minimal; no private API is bound to `0.0.0.0` except the
plan-mandated machine API and SideroLink.

- **Traefik** — host network; four entrypoints bound to `${MGMT_LAN_IP}`
  (9444/9095/9411/9001). File provider only. All static config is passed as
  CLI flags; the dynamic route config is a host bind mount
  (`/opt/omni-mgmt/traefik/dynamic.yaml` → `/etc/traefik/dynamic/dynamic.yaml`).
- **Omni** — host network; listeners set in the reviewed
  `omni-config.yaml`: API `127.0.0.1:8443` (cleartext h2c), k8s-proxy
  `127.0.0.1:8095` (TLS, internal CA with IP SAN), machine API `0.0.0.0:8090`
  (LAN/VPN direct from Talos nodes). `SSL_CERT_FILE` points at a trust
  bundle (distro roots + mgmt CA) so the Omni OIDC client trusts the
  self-signed Pocket ID issuer — `auth.oidc` has no CA-override field, so
  the container trust store is the only lever.
- **Pocket ID** — bridge network; fronts itself with internal Caddy on
  `:80`. Published to host loopback only (`127.0.0.1:80:80`); Traefik
  (host network) reaches it at `127.0.0.1:80`. Never exposed on the LAN.
- **Uptime Kuma** — bridge network, published to host loopback only
  (`127.0.0.1:3001`).
- **Provider** — host network (opt-in profile) so it reaches the loopback
  Omni API; `OMNI_ENDPOINT` is the fixed loopback path for the same-VM
  internal use.

## Bring-up order

1. Create the host directories and one-time values on the VM (see
   `home-prod/docs/management-stack.md` "Generate one-time values"):
   `/opt/omni-mgmt/omni` (state), `/opt/omni-mgmt/omni-config` (config +
   `omni.asc` + `tls/`), `/opt/omni-mgmt/pocket-id` (state, owned
   `1000:1000`),
   `/opt/omni-mgmt/omni-k8s-ca/` (internal CA + k8s-proxy cert with
   `IP:192.168.1.51` SAN), `/opt/omni-mgmt/mgmt-tls/` (mgmt cert with
   `IP:192.168.1.51` SAN), `/opt/omni-mgmt/mgmt-ca/combined-ca-bundle.pem`
   (distro roots + mgmt CA, for Omni's `SSL_CERT_FILE`),
   `/opt/omni-mgmt/traefik/dynamic.yaml` (static routes).
   **Prerequisite:** `/dev/net/tun` must exist on the VM. Omni v1.12.2
   always creates a WireGuard device at startup (kernel `wg` module,
   falling back to `/dev/net/tun` userspace) — there is no config option
   to skip it. On an LXC where `mknod` is blocked, the device node must
   be created with `sudo mknod /dev/net/tun c 10 200` and a boot hook
   added for persistence (the LXC `/dev` is a tmpfs, wiped on restart).
2. Stage the dependencies **before** Omni, so Omni finds a running issuer
   and proxy on first start (no restart loop):
   ```sh
   docker compose up -d pocket-id traefik uptime-kuma
   ```
   Then create the operator user and the Omni OIDC client in Pocket ID
   (`/setup`), complete `omni-config.yaml` (client ID/secret, account
   UUID, etcd GPG key), and start Omni:
   ```sh
   docker compose up -d omni
   ```
3. Verify HTTPS on all four entrypoint ports (self-signed IP-SAN cert) and
   the Omni login flow.

## Provider enablement gate

The Proxmox provider starts **only** with an explicit opt-in:

```sh
docker compose --profile provider up -d omni-infra-provider-proxmox
```

Before enabling, complete the Proxmox cluster prerequisites (the
`omni-proxmox-cluster` skill) and create the least-privilege Proxmox
token; PVE-version-dependent ACL verification is an operator gate, not an
assumed least privilege. Provider TLS: CA-signed Proxmox — mount the
Proxmox API CA as `pve-ca-bundle.pem` (`SSL_CERT_FILE`); the bundle must
retain the public roots plus the PVE CA. Self-signed Proxmox —
`insecureSkipVerify: true` in the provider `config.yaml`, no bundle.

## Portainer variables (UI, no env_file)

| Variable | Used by | Notes |
|---|---|---|
| `MGMT_LAN_IP` | traefik, omni | management VM LAN/VPN address the entrypoints bind to (192.168.1.51) |
| `POCKET_ID_APP_URL` | pocket-id | issuer URL, `https://192.168.1.51:9411` |
| `TZ` | all | time zone (default UTC) |
| `OMNI_STATE_DIR` | omni | host path for durable state (default `/opt/omni-mgmt/omni`) |
| `OMNI_CONFIG_DIR` | omni | host path for reviewed config (default `/opt/omni-mgmt/omni-config`) |
| `OMNI_TRUST_BUNDLE` | omni | distro roots + mgmt CA bundle for `SSL_CERT_FILE` (default `/opt/omni-mgmt/mgmt-ca/combined-ca-bundle.pem`) |
| `MGMT_TLS_DIR` | traefik | dir holding `mgmt.crt`/`mgmt.key` (default `/opt/omni-mgmt/mgmt-tls`) |
| `MGMT_TRAEFIK_DIR` | traefik | dir holding `dynamic.yaml` (default `/opt/omni-mgmt/traefik`) |
| `POCKET_ID_STATE_DIR` | pocket-id | host path for state (SQLite + uploads + JWT keys; default `/opt/omni-mgmt/pocket-id`) |
| `PROVIDER_KEY` | provider | infra provider key; injected via env, never argv (provider profile only) |
| `PROVIDER_CONFIG_DIR` | provider | host path to the provider `config.yaml` (provider profile only) |
| `PVE_CA_BUNDLE` | provider | Proxmox API CA bundle; **CA-signed clusters only** — self-signed clusters use `insecureSkipVerify: true` in `config.yaml` and omit this |

Dropped vs the hostname design: `ACME_EMAIL`, `CF_DNS_API_TOKEN`,
`OMNI_CONFIG_REF`, `OMNI_HOSTNAME`, `OMNI_K8S_HOSTNAME`,
`POCKET_ID_HOSTNAME`, `MONITOR_HOSTNAME`.

The provider's `OMNI_ENDPOINT` is the fixed loopback
`http://127.0.0.1:8443` (same-VM internal path); it is not a UI variable.

Uptime Kuma monitors, SMTP notification and email alerts are configured in
its UI (the pinned release does not read `SMTP_*` environment variables).

## Config placement

Portainer CE deploys a repository stack from the server-side image, and it
**drops compose `configs:`** — so the route config is a host bind mount
(`${MGMT_TRAEFIK_DIR:-/opt/omni-mgmt/traefik}/dynamic.yaml` →
`/etc/traefik/dynamic/dynamic.yaml`), created by the install script. There is
**no git-sync sidecar and no `omni-config` volume**. Route changes are a host
file edit → restart the Traefik container (or `docker compose up -d traefik`).

**Separation of secrets from config:** the operator-protected host files —
Omni `omni-config.yaml` + `omni.asc`, the mgmt + internal CAs/certs, the
provider `config.yaml`, the Pocket ID key, and every `${VAR}` value — stay
on the management host and are never checked in.

## Pocket ID state and key ownership

The Pocket ID image creates its own user from `PUID`/`PGID` (default
`1000`) and chowns `/app/backend/data` to match. The state directory is
created on the host owned `1000:1000`:

```sh
chown -R 1000:1000 /opt/omni-mgmt/pocket-id
```

There is **no `encryption.key` file** in v0.53.0: the JWT signing key
auto-generates inside `data/keys/jwt_private_key.json` on first start, so
the durable state directory *is* the key material. Back it up with the
database, never expose it, and restoring the directory restores the key.

## Backups and recovery

Native consistent exports (Omni etcd/datastore, Pocket ID database, monitor
state), encrypted before off-site upload, are specified in
`home-prod/docs/management-stack.md`. A live embedded etcd directory copy
is not a consistent backup. Break-glass material (account UUID, etcd GPG
key, datastore recovery) is stored independently of the managed cluster.
The mgmt CA + `mgmt.key` and the internal CA + k8s-proxy key are part of
the backup set: losing a CA means regenerating the cert pair and updating
every consumer (Traefik tlsStore, k8sproxy serversTransport, Omni trust
bundle).
