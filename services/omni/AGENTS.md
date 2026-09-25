# Management stack

Outside-cluster management Compose stack (home-prod plan §5, IP-only
/self-signed variant): self-hosted Omni, the Omni-only Pocket ID instance,
the official Proxmox infrastructure provider, a stock-Traefik management
reverse proxy and the outside-cluster availability monitor. It runs on the
management VM `cloud@192.168.1.51` and is the first service group of the
migration.

Endpoints are LAN/VPN-only, reached by IP on dedicated ports (no DNS):
`9444` Omni, `9095` Omni k8s-proxy, `9411` Pocket ID, `9001` Uptime Kuma,
plus direct `8090/tcp` (Omni machine API) and `50180/udp` (SideroLink).

- Stack layout, topology, bring-up order, the provider enablement gate,
  Portainer variables, Pocket ID ownership and backup/recovery:
  `.agents/skills/omni-management-stack/SKILL.md`.
- Proxmox clustering prerequisites and the safe seed-vs-join checklist:
  `.agents/skills/omni-proxmox-cluster/SKILL.md`.
- The omni-config example and the full deployment/operations procedure
  live in `home-prod/bootstrap/management/` and
  `home-prod/docs/management-stack.md`.
- Management-host downtime is accepted and must not stop household
  identity or existing Kubernetes workloads.
