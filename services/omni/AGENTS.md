# Management stack

Outside-cluster management Compose stack (home-prod plan §5): self-hosted
Omni, the Omni-only Pocket ID instance, the official Proxmox infrastructure
provider, a stock-Traefik management reverse proxy, the outside-cluster
availability monitor and a git-sync config sidecar. It runs on the TrueNAS
SCALE host as a Portainer CE edge stack, and browser-facing endpoints use
public hostnames under one management subzone with Let's Encrypt DNS-01 via
Cloudflare (see the skill for why an IP + private CA cannot support
passkeys).

- Stack layout, topology, bring-up order, the provider enablement gate,
  Portainer variables, git-sync config placement, Pocket ID ownership and
  backup/recovery: `.agents/skills/omni-management-stack/SKILL.md`.
- Proxmox clustering prerequisites and the safe seed-vs-join checklist:
  `.agents/skills/omni-proxmox-cluster/SKILL.md`.
- Bootstrap inputs, the management DNS helper and the full
  deployment/operations procedure live in
  `home-prod/bootstrap/management/` and
  `home-prod/docs/management-stack.md`.
- Endpoints are LAN/VPN-only. Management-host downtime is accepted and
  must not stop household identity or existing Kubernetes workloads.
