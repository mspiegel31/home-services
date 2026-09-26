---
name: omni-management-stack
description: Bring up, update, and operate the outside-cluster management Compose stack (Omni, Omni-only Pocket ID, stock-Traefik reverse proxy, Uptime Kuma, opt-in Proxmox infra provider, git-sync config sidecar) deployed as a Portainer CE edge stack on the TrueNAS SCALE host. Browser-facing endpoints use public hostnames under one management subzone with Let's Encrypt DNS-01 via Cloudflare. Use when the user asks to deploy, stage, debug, redeploy, or back up the management stack, set its Portainer variables, enable the Proxmox provider, or change the Traefik route config. Don't use for Proxmox cluster formation from standalone hosts (see omni-proxmox-cluster), household Pocket ID, or in-cluster Kubernetes work.
---

# Management Stack

Deploy and operate the outside-cluster management Compose stack (home-prod
plan §5) from `services/omni/docker-compose.yml` in this repository:
self-hosted Omni, the Omni-only Pocket ID instance, the official Proxmox
infrastructure provider, a stock-Traefik management reverse proxy, the
outside-cluster availability monitor, and a git-sync config sidecar.

It runs on the **TrueNAS SCALE host** (`192.168.1.39`, bare-metal Docker)
alongside the household application stacks, as a **Portainer CE edge stack**
on the `truenas` environment. Bootstrap inputs (DNS record allowlist, Omni
config example) live in `home-prod/bootstrap/management/`; the full
deployment/operations procedure lives in `home-prod/docs/management-stack.md`.

**Hard rules:**
- A plain deployment **never** starts the Proxmox provider. Only the
  `provider` profile does. Initial bring-up must not mutate Proxmox.
- Endpoints are LAN/VPN-only. Management-host downtime is accepted and must
  not stop household identity or existing Kubernetes workloads.
- Secrets never enter this repository. Only the non-secret proxy config
  (`traefik/dynamic.yaml`) is tracked; everything else is operator-protected
  on the host.

## Why public hostnames instead of an IP + private CA

This is not cosmetic, and reverting to an IP-only design breaks passkeys:

- **WebAuthn requires a domain-shaped RP ID.** At an `https://<ip>` origin
  the browser rejects credential creation outright with
  `SecurityError: This is an invalid domain`, before contacting any
  authenticator. `GET /api/webauthn/register/start` still returns `200` in
  that case and `/register/finish` is never posted — it reads like a server
  fault but is the client refusing the RP ID.
- **A private CA forces per-client trust imports**, and Firefox blocks
  WebAuthn entirely on origins reached through a certificate *exception*
  (Mozilla bug 1977284). Trusting the CA as a root is mandatory; an
  exception is not a substitute.
- **DNS-01 needs no inbound reachability**, so the names resolve to a
  private LAN address and nothing is exposed to the internet.
- The management subzone is **separate from the application namespace** so
  it cannot collide with the public proxy records already published for the
  application zone.

Passkeys are bound to the RP ID, so **changing the issuer hostname
invalidates existing passkeys** — re-enrolment is required, and
`POST /api/one-time-access-token/setup` only works while the initial admin
has no WebAuthn credential.

## Stack

| Service | Image | Role |
|---|---|---|
| `omni` | `ghcr.io/siderolabs/omni:v1.12.2` | Node lifecycle + cluster management; embedded etcd, OIDC to Pocket ID, break-glass enabled |
| `pocket-id` | `ghcr.io/pocket-id/pocket-id:v2.16.0` | Omni-only identity; separate issuer/DB/key/clients from any household instance |
| `traefik` | `traefik:v3.7.6` (pinned digest) | Management HTTPS; wildcard certificate via public DNS-01 using the Cloudflare provider bundled in the stock image |
| `uptime-kuma` | `ghcr.io/louislam/uptime-kuma:2.5.5` | Outside-cluster availability monitor, SMTP notifications via UI config |
| `omni-infra-provider-proxmox` | `ghcr.io/siderolabs/omni-infra-provider-proxmox:v0.3.0` | Proxmox VM provisioning; **opt-in profile, disabled by default** |
| `git-sync` | `registry.k8s.io/git-sync/git-sync:v4.4.2` (pinned digest) | Delivers the non-secret proxy config (`traefik/dynamic.yaml`) into a shared volume; anonymous HTTPS (public repo) |

## Topology

Loopback-minimal; no private API is bound to `0.0.0.0` except the
plan-mandated machine API. External LAN/VPN exposure is exactly
`9443/tcp` (Traefik TLS), `8090/tcp` (Omni machine API) and
`50180/udp` (SideroLink WireGuard).

- **Traefik** — host network; binds `192.168.1.39:9443` (TLS, DNS-01).
  This is the **only** listener: TrueNAS owns 80/443 for its own UI, and
  Host-based routing means no per-service host ports exist. File provider
  only: no Docker socket, no labels provider, no dashboard. All static
  config is CLI flags; the dynamic route config is a native Go template
  rendered from `{{ env "..." }}`, placed by the `git-sync` sidecar.
- **Omni** — host network; listeners set in the reviewed
  `omni-config.yaml`: API `127.0.0.1:8443` (cleartext h2c), k8s-proxy
  `127.0.0.1:8095` (TLS, internal CA), machine API `0.0.0.0:8090`
  (LAN/VPN direct from Talos nodes).
- **Pocket ID / Uptime Kuma** — bridge network, published to host loopback
  only (`127.0.0.1:1411`, `127.0.0.1:3001`); Traefik reaches them there.
- **Provider** — host network (opt-in profile) so it reaches the loopback
  Omni API. External clients still use HTTPS.

`/dev/net/tun` is **mandatory** and already present on this host. Omni
v1.12.2 uses only userspace wireguard-go for SideroLink: its siderolink
manager always passes a non-nil `Bind` and a non-empty
`InputPacketFilters`, and siderolabs/siderolink forces userspace whenever
either is set (`ForceUserspace = ForceUserspace || Bind != nil ||
InputPacketFilters != nil`), so the native kernel-wg branch is unreachable.
There is no configuration option to skip it.

Routes (single `:9443` listener; one hostname each):

| Hostname | Upstream |
|---|---|
| `omni.<MGMT_DOMAIN>` | `h2c://127.0.0.1:8443` (gRPC-capable) |
| `omni-k8s.<MGMT_DOMAIN>` | `https://127.0.0.1:8095` (internal CA trusted, SNI pinned) |
| `pocket-id.<MGMT_DOMAIN>` | `http://127.0.0.1:1411` |
| `monitor.<MGMT_DOMAIN>` | `http://127.0.0.1:3001` |
| anything else | Traefik default 404 (no catch-all router) |

## Certificates

One **wildcard** certificate per management subzone. All four routers carry
the same `tls.domains` block, so Traefik performs exactly one DNS-01 order
for `*.<MGMT_DOMAIN>` and reuses that certificate for every SNI name. A
router with `certResolver` but no `domains` would instead issue a separate
certificate per hostname and consume an ACME order each time.

**Two traps in `traefik/dynamic.yaml`** — both silent until deploy:

1. The template file must be valid YAML *including* the placeholder text,
   so `main:` and the wildcard entry are single-quoted. Unquoted, `{{` is
   parsed as a YAML flow mapping and `*` as an alias.
2. Do **not** put quotes inside the templated value to achieve (1).
   Traefik parses the YAML first and templates the resulting *value*, so
   `'"*.{{ env "MGMT_DOMAIN" }}"'` yields a domain string with literal
   quote characters, and ACME then tries to order a certificate for
   `"*.…"`. Verify with the Traefik API (`/api/http/routers`) that `sans`
   reads `*.mgmt.example.net`, not `"*.mgmt.example.net"`.

## DNS

Four A records (or one wildcard) pointing at the host address:

```text
omni.<MGMT_DOMAIN>      A  192.168.1.39
omni-k8s.<MGMT_DOMAIN>  A  192.168.1.39
pocket-id.<MGMT_DOMAIN> A  192.168.1.39
monitor.<MGMT_DOMAIN>   A  192.168.1.39
```

Two resolution hazards:

- **DNS rebinding protection.** Gateways (UniFi) and some resolvers refuse
  public names that resolve to private addresses. Allow-list the management
  subzone, or the names fail to resolve and it looks like a stack fault.
- **The host itself must resolve them.** Omni reaches the Pocket ID issuer
  by hostname, so the TrueNAS host's resolver must return the private
  address too. If it does not, add a host override rather than weakening the
  issuer URL.

## Bring-up order

1. Create the host directory tree on TrueNAS under
   `/mnt/tank/container-configs/omni-mgmt/` (repo convention for services on
   this host, so ZFS snapshots and backups cover it):
   `omni/` (state), `omni-config/` (reviewed config + `omni.asc` + internal
   TLS), `pocket-id/`, `pocket-id-key/encryption.key`, `omni-k8s-ca/ca.crt`,
   `provider/`, `pve-ca-bundle.pem`, `git/`, `acme/`, `kuma/`.
   Then fix ownership for the identity service:
   ```sh
   chown -R 1000:1000 /mnt/tank/container-configs/omni-mgmt/pocket-id
   ```
2. Create the scoped Cloudflare API token (Zone → DNS → Edit, limited to
   the management zone only) and the four DNS records.
3. Create the edge stack in Portainer (Edge Stacks → Add stack → Repository)
   pointing at this repository, the compose path
   `services/omni/docker-compose.yml`, and the branch or SHA you intend to
   run; set every variable from the table below. `OMNI_CONFIG_REF` must
   match the deployed ref.
4. Let the first stage come up (git-sync → traefik → pocket-id → kuma), then
   create the operator user and passkey at
   `https://pocket-id.<MGMT_DOMAIN>:9443/setup`, register the Omni OIDC
   client, complete `omni-config.yaml` (client ID/secret, account UUID, etcd
   GPG key), and redeploy so `omni` starts.
5. Verify: certificates issued (green padlock, no trust import), the four
   hostnames resolve and route, and the Omni login flow completes.

## Provider enablement gate

The Proxmox provider starts **only** with an explicit opt-in (enable the
`provider` profile for the stack). Before enabling, complete the Proxmox
cluster prerequisites (the `omni-proxmox-cluster` skill) and create the
least-privilege Proxmox token; PVE-version-dependent ACL verification is an
operator gate, not an assumed least privilege. The provider connects with
verified TLS against `pve-ca-bundle.pem`, which must retain the public roots
plus the PVE CA; do not use `insecureSkipVerify`.

## Portainer variables (UI, no env_file)

Required values use the fail-fast `${VAR:?message}` form, so a missing value
fails the deployment loudly instead of resolving to an empty string.

| Variable | Used by | Notes |
|---|---|---|
| `TZ` | all | time zone |
| `PUID`, `PGID` | pocket-id | container user for `/app/data`; use a dedicated app uid/gid on the host |
| `ACME_EMAIL` | traefik | ACME account email for DNS-01 |
| `CF_DNS_API_TOKEN` | traefik | scoped Cloudflare token, **Zone:DNS:Edit for the management zone only** — never a Global API Key |
| `MGMT_DOMAIN` | traefik | the management subzone, e.g. `mgmt.example.net`; the wildcard is derived from it |
| `OMNI_HOSTNAME` | traefik | e.g. `omni.mgmt.example.net` |
| `OMNI_K8S_HOSTNAME` | traefik | e.g. `omni-k8s.mgmt.example.net` |
| `POCKET_ID_HOSTNAME` | traefik | e.g. `pocket-id.mgmt.example.net` |
| `MONITOR_HOSTNAME` | traefik | e.g. `monitor.mgmt.example.net` |
| `POCKET_ID_URL` | pocket-id | issuer URL, must match `POCKET_ID_HOSTNAME` and include the port, e.g. `https://pocket-id.mgmt.example.net:9443` |
| `OMNI_CONFIG_REF` | git-sync | config ref to sync; must match the edge-stack ref |
| `PROVIDER_KEY` | provider | infra provider key; injected via env, never argv (provider profile only) |

Host paths and the listener address are hardcoded in the compose, matching
the other stacks on this host (`/mnt/tank/container-configs/omni-mgmt/...`,
`192.168.1.39:9443`). The provider's `OMNI_ENDPOINT` is the fixed loopback
`http://127.0.0.1:8443` and is not a UI variable.

## Config placement (git-sync sidecar)

Portainer CE drops compose `configs:` and does not resolve relative
bind-mount paths, so the proxy config cannot ride in the stack definition.
The `git-sync` sidecar places the non-secret config into a shared volume:

- Image `registry.k8s.io/git-sync/git-sync:v4.4.2` (pinned digest),
  `user: "0:0"`, host bind `/mnt/tank/container-configs/omni-mgmt/git:/git`.
  The repository is public, so it pulls over anonymous HTTPS — no token.
- **No sparse-checkout file.** The upstream design passed one through
  compose `configs:`, which Portainer drops; this variant takes a full
  `--depth=1` checkout instead of adding an init container.
- Traefik mounts the same volume read-only and reads
  `/config/current/services/omni/traefik/dynamic.yaml`.
- `--providers.file.watch=false` is deliberate: after a sync, restart or
  redeploy to pick up a route change.
- The sidecar's healthcheck asserts the route file exists (the file provider
  loads it once at startup, so a missing file means no routes at all) and
  that its HTTP endpoint answers; Traefik depends on that health.

**Separation of secrets from config:** the operator-protected host files —
Omni `omni-config.yaml` + `omni.asc`, the provider `config.yaml`, the Pocket
ID encryption key, the internal CA, the PVE CA bundle, and all `${VAR}`
values — stay on the host and are never checked in. Only the non-secret
proxy config travels through git-sync.

## Pocket ID state and key ownership

v2.x renamed these from the v0.53.x names — do not copy environment from the
older IP-only stack:

| v2.x | v0.53.x |
|---|---|
| `APP_URL` | `PUBLIC_APP_URL` |
| `UI_CONFIG_DISABLED` | `PUBLIC_UI_CONFIG_DISABLED` |

Image contract verified against v2.16.0 source and image: entrypoint
`/app/docker/entrypoint.sh`, binary `/app/pocket-id`, state `/app/data`
(chowned to `PUID`/`PGID` by the entrypoint), port `1411/tcp`, and the image
supplies its own healthcheck (no override needed). `ENCRYPTION_KEY_FILE`
must contain **at least 16 bytes** (`openssl rand -base64 32`).

State and key directories are created on the host owned by the container
user; do **not** use `chmod 777`. The tag is `v2.16.0` **with the `v`** —
`2.16.0` does not exist and fails as `manifest unknown`.

## Backups and recovery

All durable state lives under `/mnt/tank/container-configs/omni-mgmt/`, so
it is covered by the existing ZFS snapshot and backup policy: Omni's
embedded etcd + sqlite, the Pocket ID database **and its encryption key**,
Kuma's state, and Traefik's `acme/` (account key + issued certificates —
losing it means re-issuing on every restart and risking the ACME rate
limits). A live embedded etcd directory copy is not a consistent backup.
Break-glass material (account UUID, etcd GPG key, datastore recovery) is
stored independently of the managed cluster.

Restoring Pocket ID without its `encryption.key` leaves stored secrets
unreadable; the two belong together in the backup set.