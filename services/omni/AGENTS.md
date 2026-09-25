# Management stack

Outside-cluster management Compose stack (home-prod plan §5): self-hosted
Omni, the Omni-only Pocket ID instance, the official Proxmox infrastructure
provider, a stock-Traefik management reverse proxy and the outside-cluster
availability monitor. It runs on a dedicated general-purpose VM on the
management host and is the first service group of the migration.

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
