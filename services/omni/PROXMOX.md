# Proxmox cluster formation: operator checklist

Purpose: form the three-node Proxmox management cluster from the current
standalone hosts, evacuate and restore existing guests safely, and establish
the prerequisites for the pinned Omni Proxmox provider. This document is a
checklist of facts to collect and gates to pass. It is not a copy-paste
script: every command takes site-specific values that only the operator has.

## Sources

- Cluster manager (pvecm, quorum, join, corosync network):
  https://pve.proxmox.com/pve-docs/chapter-pvecm.html
- HA manager (requirements, affinity, fencing, watchdog):
  https://pve.proxmox.com/pve-docs/chapter-ha-manager.html
- QEMU VM management (migration requirements, passthrough limits):
  https://pve.proxmox.com/pve-docs/chapter-qm.html
- Backup (vzdump modes, backup storage, restore):
  https://pve.proxmox.com/pve-docs/chapter-vzdump.html
- User management (API tokens, roles, privileges, ACL paths):
  https://pve.proxmox.com/pve-docs/chapter-pveum.html
- Firewall (per-VM fwbr bridge behavior):
  https://pve.proxmox.com/pve-docs/chapter-pve-firewall.html
- Omni Proxmox provider (pinned v0.3.0):
  https://github.com/siderolabs/omni-infra-provider-proxmox/tree/v0.3.0
  (README, `cmd/omni-infra-provider-proxmox/data/schema.json`,
  `internal/pkg/provider/{data,provision}.go`, `internal/pkg/config/config.go`)

## What this cluster does and does not provide

| Capability | After clustering (local storage, this plan) |
|---|---|
| Unified cluster config (users, ACLs, storage defs, jobs, firewall) | Yes, replicated via pmxcfs |
| Quorum-governed cluster operations | Yes; cluster is read-only when inquorate |
| Guest failover on host loss | Not selected in this plan |
| Proxmox HA resources | Not configured in this plan (provider `ha:` block requires PVE 9+) |
| Live migration of the Talos VMs | Supported by Proxmox for VMs without locally bound resources (local disks can be sent to the target; PCI/USB passthrough blocks live migration, per qm docs). Not relied on in this plan: Talos VMs are host-bound by decision, the GPU VM uses passthrough |

Kubernetes/Longhorn (planned) handles workload recovery. This cluster is for
management and config replication only.

## 1. Per-host fact table (blank rollout inputs)

Collect from each of the three physical hosts before any change. Do not guess.

| Fact | Host A | Host B | Host C |
|---|---|---|---|
| Proxmox VE version (`pveversion`) | | | |
| Current node name | | | |
| Final node name (decide before `pvecm create`; corosync is IP-keyed) | | | |
| Management IP (current) | | | |
| Management IP (final; static, DHCP-excluded) | | | |
| NTP source and sync status (`timedatectl status`) | | | |
| Guest count, VMID list, and running/stopped state (`pvesh get /cluster/resources`) | | | |
| Storage IDs, types, paths, free space (`pvesm status`) | | | |
| VM storage chosen for Talos VMs (ID, free space per plan capacity gates) | | | |
| ISO storage (ID, free space) | | | |
| Bridge name for Talos VMs (e.g. `vmbr0`) | | | |
| VLAN tag (if any) | | | |
| Passthrough devices (GPU, optical, USB) and resource mapping names | | | |
| Cluster-network candidate interface and IP (<5 ms latency to the other two hosts) | | | |
| Outbound internet access to image factory (yes/no) | | | |

## 2. Seed vs joining nodes

- **Seed node** (`pvecm create CLUSTERNAME`): may keep its existing guests.
  Cluster creation on this node does not require guest evacuation. Choose
  the seed as the host that is hardest to evacuate (most guests, most
  passthrough devices, least redundant), so that only the two easier hosts
  need evacuation. Back up the seed node's guests and configuration as well;
  a backup is a backup regardless of which node joins.
- **Joining nodes** (`pvecm add IP-CLUSTER`): **must be empty of guests**
  before joining. Joining overwrites `/etc/pve`, guest IDs must not conflict
  with the cluster, and the node inherits the cluster's storage
  configuration. The documented path for a populated joining node is:
  vzdump every guest -> evacuate -> join empty -> restore under new IDs ->
  re-add node-specific storages with node restrictions.

## 3. Evacuation and restore rehearsal (one node at a time)

For each joining node, before joining:

1. **Identify a backup storage** reachable from that node with enough space
   for every guest on it (NFS share, local disk, or Proxmox Backup Server).
   Record the storage ID.
2. **Back up every guest** on the node. Official vzdump modes: `snapshot`
   (default, live backup), `stop` (orderly shutdown, highest consistency),
   `suspend` (compat). Record backup file names and paths.
3. **Restore rehearsal**: restore at least one representative guest backup to
   a new VMID (scratch) on the same node or a staging node. The scratch VM
   must be isolated from production services before it boots: use a
   dedicated test bridge/VLAN with no production IP range, disable or
   exclude passthrough devices, and ensure no external writer (database
   replica, sync target, MQTT consumer) can reach it. Do not boot a
   production clone on the production LAN. Verify it boots and its data is
   intact, then stop and delete the scratch VM. A backup that has not been
   restored is not a verified backup.
4. **Plan target VMIDs** in the cluster for each evacuated guest. They must
   not collide with existing cluster IDs. Record the mapping
   (old VMID -> new VMID -> target storage) and the intended running/stopped
   state for each guest after restore.
5. **Record per-guest context** that does not travel in the backup:
   passthrough mappings, IP reservations, DNS records, node-specific
   firewall rules, bridge/VLAN assignments.

Maintenance boundary: evacuate and rejoin one node at a time. Do not join
both remaining nodes in parallel. After each join, verify `pvecm status`
shows the expected node count and quorate state before proceeding to the
next node.

## 4. Network, time, and quorum prerequisites

Before `pvecm create`:

- [ ] All three nodes synchronized to the same NTP source.
- [ ] UDP ports 5405-5412 reachable between all node pairs (corosync).
- [ ] TCP port 22 (SSH) reachable between all node pairs.
- [ ] Cluster-network link measured: ping all six pairs; latency < 5 ms
      (the documented requirement). If the hosts share a single NIC, record
      the measured latency as a gate; >10 ms is not guaranteed to work.
- [ ] Root password available on each node (required for join).
- [ ] Final node names and IPs fixed before `pvecm create`. Corosync
      membership is keyed to static addresses. Renaming a cluster node after
      formation is a version-specific procedure; finalize names now to avoid
      it.
- [ ] Decision: dedicated cluster network link, or shared with the
      management/VM network. If shared, document the latency measurement.
- [ ] If the Proxmox firewall is enabled, corosync ACCEPT rules are
      generated automatically; verify no other rule blocks UDP 5405-5412.

Quorum: three nodes, one vote each; a majority (2 of 3) is required. A
transient two-node state during formation requires both votes; a QDevice is
the documented option for a permanent two-node cluster, not mandatory for
brief formation windows.

## 5. Cluster formation sequence

Execute in order. Do not skip the verification step after each action. This
sequence requires live operator authorization; no live actions are executed
by this document or by implementation work.

1. **Seed node**: `pvecm create CLUSTERNAME` (choose a unique cluster name).
   Verify with `pvecm status`. The seed node keeps its guests.
2. **Joining node 1** (already evacuated per section 3): on that node,
   `pvecm add IP-SEED-NODE`. This authenticates against the seed node's API
   with root@pam and verifies the SHA-256 certificate fingerprint. Verify
   `pvecm status` on the seed node shows two nodes, quorate.
3. **Joining node 2** (already evacuated): repeat step 2. Verify three
   nodes, quorate.
4. **Re-add per-node local storages** on each node with their `nodes`
   restriction set to that node only, so local storage is not visible
   cluster-wide.
5. **Restore evacuated guests** under their planned new VMIDs (section 3,
   step 4). Restore each guest to its intended prior running/stopped state.
   Verify each guest boots (if intended running) and its data is intact.
6. **Post-join CA trust refresh**: after joining, each node's certificate is
   re-issued by the cluster CA. Any client that pinned the old per-node
   certificate (web UI sessions, API clients, the Omni provider) must trust
   the new cluster CA. For the provider, the CA must be trusted **inside the
   provider container** (host trust store alone is insufficient for a
   containerized client); see [README](README.md) for the mount arrangement.
   Do not use `insecureSkipVerify` in the provider config;
   TLS verification against the cluster CA is required.
7. **Verify end state**: `pvecm status` on all three nodes shows three
   nodes, quorate, correct cluster name. All evacuated guests are running in
   their intended states. Storage restrictions are correct.

## 6. Omni Proxmox provider prerequisites (pinned v0.3.0)

Image: `ghcr.io/siderolabs/omni-infra-provider-proxmox:v0.3.0`.
Verify Omni CLI compatibility with this provider version at pin time in the
isolated validation wave.

### Provider connection config

```yaml
proxmox:
  url: "https://<cluster-node>:8006/api2/json"
  tokenID: <token-id>
  tokenSecret: <secret>
```

- Any cluster node's API address works (cluster API is per-node; data is
  replicated via pmxcfs).
- TLS: trust the cluster CA inside the provider container. Do not set
  `insecureSkipVerify`.
- The provider host needs LAN reachability to the cluster (TCP 8006).

### Machine class provider data (per the plan: one Talos VM per host)

Required fields (provider schema): `cores`, `memory` (MB), `disk_size` (GB),
`storage_selector` (CEL expression, e.g. `name == "local-lvm"`). Size values
come from the plan's capacity gates (migration plan section 3), not from
provider defaults.

Per-host fields:
- `node`: the Proxmox node name (pins the VM to that host).
- `network_bridge`: the bridge for the Talos VM (default `vmbr0`).
- `vlan`: VLAN tag if any.
- `network_firewall`: provider default is `true` (primary NIC gets the
  per-VM fwbr firewall bridge). Verify the Talos 1.13 Layer2VIPConfig works
  with fwbr before the first VM boots. If a measured VIP failure occurs,
  investigate it and review any firewall change (including setting `false`)
  as a separate security decision; do not assume the NIC flag is the only
  firewall boundary for the VM.
- GPU host only: `pci_devices` (resource mapping name), `machine_type: q35`,
  `cpu_type: host`, `balloon: false`. Model-data disk as an
  `additional_disks` entry with its own `storage_selector`.
- `ha`: do **not** set. The block requires PVE 9+; this plan makes no
  Proxmox HA promise and uses local storage.

### ISO download (not templates)

The provider does not clone from a template. It resolves the Talos ISO from
the Omni image-factory API and downloads it into each node's ISO storage
(`storage.DownloadURL`). Prerequisites:

- [ ] An ISO storage exists on each of the three nodes with free space for
      the Talos ISO.
- [ ] Each Proxmox node has outbound network access to the image-factory URL
      that Omni returns. If a node is offline, pre-seed the ISO in its ISO
      storage manually; the provider checks for an existing ISO before
      downloading.
- [ ] The Talos ISO is built with `qemu-guest-agent` (an image-factory
      extra, not a Proxmox concern).

### Token permission verification (per-endpoint gate)

Create a dedicated Proxmox user (e.g. `omni` in the `pve` realm, i.e.
`omni@pve`) and a separated-privilege API token. The token's effective
permissions are the intersection of user and token ACLs.

Do not apply a pre-built ACL set. Instead, verify each endpoint the v0.3.0
source calls against the pinned PVE version's API permission tables
(https://pve.proxmox.com/pve-docs/api-viewer/). The endpoints to check, from
`internal/pkg/provider/provision.go` and `internal/pkg/provider/ha/manager.go`:

| Provider API call | What it does |
|---|---|
| `cluster.NextID` | Allocate the next cluster-wide VMID |
| `node.Status` / `node.Storage` listing | Read node state and storage (scheduler) |
| `node.StorageISO` + `storage.DownloadURL` | Download the Talos ISO into the node's ISO storage |
| `vm.Create` | Create the VM (disks, NICs, CPU, memory, PCI/USB mappings) |
| `vm.CloudInit` | Inject nocloud config |
| `vm.Start` | Start the VM |
| VM delete (deprovision) | Remove the VM on teardown |
| Pool create/delete | Manage a pool per machine request set |
| HA resource/rule API | Only if `ha:` is ever enabled (PVE 9+); not used in this plan |

For each endpoint, record the required privilege(s) from the API viewer for
the pinned PVE version, then build the smallest ACL set that covers them.
The token secret is shown once at creation; store it in Bitwarden, never in
manifests or Git.

## 7. Blockers and open questions (operator must resolve)

- [ ] Actual PVE version on each host (must be identical across the cluster).
- [ ] Current guest/VMID inventory per node with running/stopped state (the
      evacuation list).
- [ ] Storage layout and free space per node; which storage serves the Talos
      VMs and which serves ISOs.
- [ ] Bridge/VLAN naming per node; whether the Talos L2 VIP segment crosses
      fwbr.
- [ ] Whether a physically separate cluster network exists (second NIC per
      host). If not, record the measured latency as a join gate.
- [ ] IOMMU group / whole-device passthrough confirmation for the GPU host.
- [ ] Outbound internet access from each host to the image factory, or a
      plan to pre-seed the ISO.
- [ ] Omni CLI version compatibility with provider v0.3.0 (verify in
      isolated validation).
- [ ] Token ACL verification per endpoint against the pinned PVE version
      (section 6).

## Completion criteria

- [ ] All facts in section 1 are filled in from live host data.
- [ ] All three nodes (including the seed) have verified vzdump backups;
      both joining nodes have a successful isolated restore rehearsal.
- [ ] Cluster formed: `pvecm status` shows three nodes, quorate, correct
      name, on all three hosts.
- [ ] All evacuated guests are restored in their intended prior
      running/stopped states.
- [ ] Per-node local storages have correct node restrictions.
- [ ] Cluster CA is trusted inside the provider container; TLS verification
      works (no `insecureSkipVerify`).
- [ ] ISO storage exists on all three nodes; image-factory reachability
      confirmed (or ISO pre-seeded).
- [ ] Provider token created; per-endpoint privileges verified against the
      pinned PVE version; ACLs applied to match; secret in Bitwarden.
- [ ] No `ha:` block in any machine class config.
