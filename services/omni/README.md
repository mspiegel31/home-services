# Management stack

Outside-cluster management Compose stack (home-prod plan §5): self-hosted
Omni, the Omni-only Pocket ID instance, the official Proxmox infrastructure
provider, a Traefik management reverse proxy and the outside-cluster
availability monitor. It runs on a dedicated general-purpose VM on the
management host and is the first service group of the migration.

- Owner: this repository. Bootstrap inputs, the management DNS helper and
  the full deployment/operations procedure live in
  `home-prod/bootstrap/management/` and `home-prod/docs/management-stack.md`.
- Proxmox clustering prerequisites and the safe seed-vs-join checklist:
  [PROXMOX.md](PROXMOX.md).
- Endpoints are LAN/VPN-only. Management-host downtime is accepted and
  must not stop household identity or existing Kubernetes workloads.

## Stack

| Service | Image | Role |
|---|---|---|
| `omni` | `ghcr.io/siderolabs/omni:v1.12.2` | Node lifecycle + cluster management; embedded etcd, OIDC to Pocket ID, break-glass enabled |
| `pocket-id` | `ghcr.io/pocket-id/pocket-id:2.16.0` | Omni-only identity; separate issuer/DB/keys/clients from the household instance |
| `traefik` | `traefik:latest` (pinned tag) | Management HTTPS; public DNS-01 via bundled Cloudflare provider (scoped token), h2c upstream to Omni |
| `uptime-kuma` | `ghcr.io/louislam/uptime-kuma:2.5.5` | Outside-cluster availability monitor, SMTP notifications via UI config |
| `omni-infra-provider-proxmox` | `ghcr.io/siderolabs/omni-infra-provider-proxmox:v0.3.0` | Proxmox VM provisioning; **opt-in profile, disabled by default** |

## Bring-up order

1. Create the host directories and one-time secrets on the VM (see
   `docs/management-stack.md` in home-prod for the exact procedure):
   `/opt/omni-mgmt/omni`, `/opt/omni-mgmt/omni-config` (config + `omni.asc`
   + internal TLS), `/opt/omni-mgmt/pocket-id` (state),
   `/opt/omni-mgmt/pocket-id-key` (`encryption.key`),
   `/opt/omni-mgmt/omni-internal-ca/ca.crt`, `/opt/omni-mgmt/provider`
   (provider `config.yaml`), `/opt/omni-mgmt/pve-ca-bundle.pem`.
2. Run the management DNS helper (home-prod
   `bootstrap/management/dns.py`) from the workstation: preview, then apply
   the local UniFi A records for the management hostnames.
3. `docker compose up -d` — starts Omni, Pocket ID, the proxy and the monitor.
   Pocket ID bootstrap works before any Omni OIDC client exists: create the
   operator user and the Omni OIDC client in the Pocket ID UI/API, then
   register them in `omni-config.yaml` and restart Omni.
4. Verify HTTPS on all three hostnames and the Omni login flow.

## Provider enablement gate

The Proxmox provider starts **only** with an explicit opt-in:

```sh
docker compose --profile provider up -d omni-infra-provider-proxmox
```

A plain `docker compose up -d` never starts it, so the initial management
bring-up cannot mutate Proxmox. Before enabling, read `PROXMOX.md` (seed
vs. joining populated nodes, guest evacuation, storage) and create the
least-privilege Proxmox token; PVE-version-dependent ACL verification is an
operator gate, not an assumed least privilege. The provider connects with
verified TLS: mount the Proxmox API CA as `pve-ca-bundle.pem`
(`SSL_CERT_FILE`); do not use `insecureSkipVerify`.

## Portainer variables (UI, no env_file)

| Variable | Used by | Notes |
|---|---|---|
| `TZ` | all | time zone |
| `MGMT_LAN_IP` | traefik, uptime-kuma | management VM LAN/VPN address the proxies bind to (default 127.0.0.1) |
| `OMNI_STATE_DIR`, `OMNI_CONFIG_DIR` | omni | host paths for durable state and reviewed config |
| `POCKET_ID_APP_URL` | pocket-id | issuer URL, e.g. `https://pocket-id.<mgmt-domain>` |
| `POCKET_ID_STATIC_API_KEY` | pocket-id | optional declarative admin API key |
| `SMTP_HOST`/`SMTP_PORT`/`SMTP_FROM`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_TLS` | pocket-id | recovery/verification email; empty leaves defaults |
| `POCKET_ID_STATE_DIR`, `POCKET_ID_KEY_DIR` | pocket-id | host paths for state and encryption key |
| `CLOUDFLARE_DNS01_TOKEN` | traefik | scoped zone token for public DNS-01; provisioned outside ESO |
| `OMNI_INTERNAL_CA` | traefik | host path to the internal CA for the proxy→Omni k8s-proxy hop |
| `PROVIDER_OMNI_API_ENDPOINT` | provider | Omni API URL with the internal CA trusted |
| `PROVIDER_KEY` | provider | infra provider key; injected via env, never argv |
| `PROVIDER_CONFIG_DIR` | provider | host path to the provider `config.yaml` (Proxmox token) |
| `PVE_CA_BUNDLE` | provider | host path to the Proxmox API CA bundle |

Uptime Kuma monitors, SMTP notification and email alerts are configured in
its UI (the pinned release does not read `SMTP_*` environment variables);
the monitor set is documented in home-prod `docs/management-stack.md`.

## Backups and recovery

Native consistent exports (Omni etcd/datastore, Pocket ID database, monitor
state), encrypted before off-site upload, are specified in
`home-prod/docs/management-stack.md`. A live embedded etcd directory copy
is not a consistent backup. Break-glass material (account UUID, etcd GPG
key, datastore recovery) is stored independently of the managed cluster.
