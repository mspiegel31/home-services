# Management stack

Outside-cluster management Compose stack (home-prod plan §5): self-hosted
Omni, the Omni-only Pocket ID instance, the official Proxmox infrastructure
provider, a stock-Traefik management reverse proxy, and a git-sync config
sidecar. It runs on the TrueNAS SCALE host as a Portainer CE edge stack,
and browser-facing endpoints use public hostnames under one management
subzone with Let's Encrypt DNS-01 via Cloudflare (rationale: home-prod
`docs/management-stack.md` → Architecture).

Ownership split:
- This directory's skill (`.agents/skills/omni-management-stack/SKILL.md`)
  holds edit-time facts: hard rules, service/image and route tables,
  Portainer variables, config-placement and templating traps.
- `home-prod/docs/management-stack.md` is the rollout document: the full
  deployment/operations procedure (host prep, bring-up, verification,
  provider enablement, backups).
- The home-prod plan §5 owns the requirements.
- Proxmox clustering prerequisites and the seed-vs-join checklist:
  `.agents/skills/omni-proxmox-cluster/SKILL.md`.
- Bootstrap inputs and the host setup script:
  `home-prod/bootstrap/management/`.

Endpoints are LAN/VPN-only. Management-host downtime is accepted and
must not stop household identity or existing Kubernetes workloads.
