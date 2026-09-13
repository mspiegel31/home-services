# AI control of Proxmox VE: options and recommendation

**Investigated:** 2026-09-09

## Verdict

**Use the Proxmox VE HTTPS API as the authority boundary.** Put a small policy adapter in front of it, authenticate with a dedicated privilege-separated API token, and let Proxmox RBAC enforce the maximum authority available to the AI. Proxmox documents the HTTPS API, its JSON Schema, token authentication, and its path-based permission system; it also publishes the API viewer and an official Perl client. ([API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API), [API viewer](https://pve.proxmox.com/pve-docs/api-viewer/), [official Perl client mirror](https://github.com/proxmox/pve-apiclient))

**An official CLI exists, but it is the wrong primary boundary for an AI.** `pvesh` exposes the API locally without the HTTPS server and only root may run it. Calling it through SSH therefore gives the automation a root-capable path that is harder to constrain than an API token. Keep SSH and `pvesh` for human-operated break-glass work. ([pvesh manual](https://pve.proxmox.com/pve-docs/pvesh.1.html), [API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API))

**No Proxmox-official or Proxmox-endorsed MCP server was found.** The official material reviewed here documents the REST API, API tokens/RBAC, `pvesh`, `pveum`, and the Proxmox-maintained Perl client, but no MCP server. None of the three relative MCP leaders reviewed below discloses an independent security audit. They are promising community adapters, not a trusted control plane. ([API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API), [pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html), [pvesh manual](https://pve.proxmox.com/pve-docs/pvesh.1.html), [Proximo](https://github.com/john-broadway/proximo), [mcp-pve](https://github.com/Samik081/mcp-pve), [proxmox-mcp](https://github.com/GethosTheWalrus/proxmox-mcp))

## Control-surface comparison

| Surface | Official and security status | Operational fit | Decision |
|---|---|---|---|
| **HTTPS REST API** | Proxmox documents a REST-like, JSON-Schema-defined API on HTTPS port 8006. API tokens support separate permissions, expiration, and revocation. ([API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API), [pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html)) | Works remotely without host shell access. The API viewer exposes endpoint schemas, and Proxmox tries to preserve API compatibility within a major release. ([API viewer](https://pve.proxmox.com/pve-docs/api-viewer/), [API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API)) | **Recommended authority boundary.** |
| **Local CLI: `pvesh`, `pveum`, and related tools** | `pvesh` is Proxmox's shell interface to the API and may be run only as root. `pveum` is the official user, role, token, and ACL manager. ([pvesh manual](https://pve.proxmox.com/pve-docs/pvesh.1.html), [pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html)) | Excellent for a human administrator on a node. Remote AI use normally adds SSH and root-level host authority; `pvesh` can also proxy calls to other cluster members over SSH. ([API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API)) | **Human-only administration and break glass.** |
| **Third-party MCP** | The reviewed implementations are community repositories outside the Proxmox GitHub organization. Their repositories show no Proxmox endorsement or disclosed independent security audit. ([Proximo](https://github.com/john-broadway/proximo), [mcp-pve](https://github.com/Samik081/mcp-pve), [proxmox-mcp](https://github.com/GethosTheWalrus/proxmox-mcp), [Proxmox client](https://github.com/proxmox/pve-apiclient)) | MCP improves tool discovery and schemas, but it adds dependencies, tool-routing code, configuration defaults, and another place where a generic or destructive call can be exposed. Each reviewed MCP ultimately relies on Proxmox credentials or, in some cases, SSH. ([Proximo security model](https://github.com/john-broadway/proximo/blob/main/SECURITY.md), [mcp-pve README](https://github.com/Samik081/mcp-pve), [proxmox-mcp README](https://github.com/GethosTheWalrus/proxmox-mcp)) | **Optional, replaceable adapter only.** |

## MCP landscape

Stars, forks, and release dates measure visible adoption and maintenance activity. They do not establish security or operational reputation.

| Candidate | Observable evidence on 2026-09-09 | Caveats | Assessment |
|---|---|---|---|
| **[Proximo](https://github.com/john-broadway/proximo)** | 43 stars and 8 forks; the repository was created in June 2026 and released v0.40.0 on September 5. Its documented controls include a recorded plan for mutations, a tamper-evident ledger, optional out-of-band consent and containment, artifact provenance, and an SBOM. ([repository metadata](https://api.github.com/repos/john-broadway/proximo), [v0.40.0](https://github.com/john-broadway/proximo/releases/tag/v0.40.0), [security model](https://github.com/john-broadway/proximo/blob/main/SECURITY.md), [verification guide](https://github.com/john-broadway/proximo/blob/main/VERIFY.md)) | One account supplies 173 of the 181 non-bot contributions shown by GitHub. The caller can pass `confirm=True`, so plan/confirm is not independent human authorization. Consent and containment are opt-in, and the project says those controls become boundaries only when their state is outside the agent's write reach. Its consent ID excludes live pre-state, so an outer broker must bind and recheck preconditions. The controls have reproducible project checks and an automated OpenSSF Scorecard, but no disclosed independent audit. Its optional container-exec path uses SSH and is not constrained by the Proxmox API token. ([contributors](https://api.github.com/repos/john-broadway/proximo/contributors?anon=1&per_page=100), [governed dispatch](https://raw.githubusercontent.com/john-broadway/proximo/main/src/proximo/server.py), [consent implementation](https://raw.githubusercontent.com/john-broadway/proximo/main/src/proximo/consent.py), [security model](https://github.com/john-broadway/proximo/blob/main/SECURITY.md), [verification guide](https://github.com/john-broadway/proximo/blob/main/VERIFY.md)) | **Strongest pilot candidate by control design; still promising, not established.** Disable SSH/exec features and require protected out-of-band consent for an API-only pilot. |
| **[Samik081/mcp-pve](https://github.com/Samik081/mcp-pve)** | 21 stars and 4 forks; v0.8.1 shipped September 2. It exposes 121 tools and supports category filters, a 54-tool read-only tier, and TLS verification by default. ([repository metadata](https://api.github.com/repos/Samik081/mcp-pve), [v0.8.1](https://github.com/Samik081/mcp-pve/releases/tag/v0.8.1), [README](https://github.com/Samik081/mcp-pve)) | GitHub lists one human contributor. The default access tier is `full`, and its whitelist can bypass tier and category filters. Optional HTTP mode binds to `0.0.0.0` by default and the server adds no client-authentication check. The README's quick start uses a `root@pam` token example and shows how to disable TLS verification; those examples should not become deployment defaults. ([contributors](https://api.github.com/repos/Samik081/mcp-pve/contributors?anon=1&per_page=100), [configuration source](https://raw.githubusercontent.com/Samik081/mcp-pve/main/src/core/config.ts), [filter source](https://raw.githubusercontent.com/Samik081/mcp-pve/main/src/core/tools.ts), [HTTP server source](https://raw.githubusercontent.com/Samik081/mcp-pve/main/src/core/server.ts), [README](https://github.com/Samik081/mcp-pve)) | **Compact and promising; requires a fail-closed configuration review.** Set `read-only`, use a non-root user, leave TLS verification on, avoid the force-include whitelist, and use stdio or an authenticated loopback proxy. |
| **[GethosTheWalrus/proxmox-mcp](https://github.com/GethosTheWalrus/proxmox-mcp)** | 182 stars and 11 forks, the largest visible adoption of these three; v1.4.1 shipped July 30. The repository includes tests, CodeQL, OSV and Docker scanning workflows, plus a vulnerability-reporting policy. ([repository metadata](https://api.github.com/repos/GethosTheWalrus/proxmox-mcp), [v1.4.1](https://github.com/GethosTheWalrus/proxmox-mcp/releases/tag/v1.4.1), [repository](https://github.com/GethosTheWalrus/proxmox-mcp), [security policy](https://github.com/GethosTheWalrus/proxmox-mcp/blob/main/SECURITY.md)) | GitHub's contributor list shows one human maintainer alongside automation. The defaults leave read-only mode off, expose a raw tool that accepts arbitrary GET, POST, PUT, or DELETE paths, disable TLS verification, and use `root@pam` when no user is set. ([contributors](https://api.github.com/repos/GethosTheWalrus/proxmox-mcp/contributors?anon=1&per_page=100), [server source](https://raw.githubusercontent.com/GethosTheWalrus/proxmox-mcp/main/src/proxmox_mcp/server.py), [client source](https://raw.githubusercontent.com/GethosTheWalrus/proxmox-mcp/main/src/proxmox_mcp/client.py), [README](https://github.com/GethosTheWalrus/proxmox-mcp)) | **Promising by adoption and automation; unsafe defaults for unattended infrastructure control.** A pilot must reverse all four defaults. |

None qualifies as “reputable” in the same sense as a vendor-supported control surface. Proximo is the best first security-oriented evaluation; GethosTheWalrus/proxmox-mcp has the strongest visible adoption; Samik081/mcp-pve documents explicit access tiers and filtering. These are relative comparisons among young community projects, not endorsements. ([Proximo metadata](https://api.github.com/repos/john-broadway/proximo), [mcp-pve repository](https://github.com/Samik081/mcp-pve), [proxmox-mcp metadata](https://api.github.com/repos/GethosTheWalrus/proxmox-mcp))

## Recommended architecture

```text
Human operator
  ├── owns policy, token grants, and one-time approvals
  └── reviews proposed mutations and recovery plans

AI agent
  │  structured intent; no token or shell access
  ▼
Replaceable adapter
  │  endpoint allowlist, schema validation, target checks, audit log
  │  optional MCP transport; no generic/raw API tool
  ▼
Approval broker
  │  read token for GET; short-lived scoped write token only after approval
  ▼
HTTPS :8006/api2/json
  ▼
Proxmox VE RBAC and path ACLs       ← authority boundary
  ▼
Named nodes, pools, guests, and storage only
```

Proxmox's permission check supplies the hard control. Model prompts and MCP tool lists do not. Proxmox calculates a privilege-separated token's effective permissions as the intersection of the backing user's permissions and the token's own ACLs. Newly created tokens use separated privileges by default; tokens can expire and can be revoked without disabling the backing user. Revocation or expiry must not be treated as cancellation of a task that has already started. ([pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html))

Implement that boundary as follows:

1. **Create a dedicated non-root automation user and one token per agent and environment.** Keep privilege separation enabled (`privsep=1`), set an expiration, and grant the backing user and token only the same required roles on the same paths. Proxmox documents both the permission intersection and commands for inspecting user and token permissions. ([pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html))
2. **Start with a read token.** Define a custom observation role from `Sys.Audit`, `VM.Audit`, `Datastore.Audit`, and `Pool.Audit`, omitting privileges that are not required. Alternatively, grant the built-in read-only `PVEAuditor` role only on the managed paths. Proxmox supports custom roles, path ACLs, and inheritance; `PVEAuditor` is read-only. ([pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html))
3. **Scope resources by path.** Prefer a dedicated resource pool for AI-visible guests, explicit node paths, and named storage paths. Do not grant `Administrator` or broad write roles at `/`. Proxmox's permissions form triples of principal, role, and path, and pool ACLs can apply to pool members. ([pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html))
4. **Separate read and write credentials.** Keep the read token available to the adapter. Store the narrower write token outside the agent's readable filesystem and release it to the broker only for one approved operation or a short approval window. Expire or revoke the write token to block future requests after the window; separately monitor or cancel any task already started. ([pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html))
5. **Keep secrets out of prompts, command arguments, and MCP configuration visible to the agent.** Proxmox warns that command-line authentication headers can be read by other users and recommends a user-readable header file instead. Use a secret manager or protected credential file and keep TLS verification enabled. ([API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API))
6. **Remove alternate authority paths.** The agent should have no SSH key for Proxmox nodes, no local root access, no `pvesh`, no console capability, and no generic shell or raw API tool. `pvesh` is root-only, and API tokens cannot access VM or system console endpoints. ([pvesh manual](https://pve.proxmox.com/pve-docs/pvesh.1.html), [pveum manual](https://pve.proxmox.com/pve-docs/pveum.1.html))
7. **Treat an MCP server as replaceable.** It may translate tool calls into approved API requests, but it receives no broader token than the direct client and cannot expand the endpoint allowlist. Pin the reviewed source revision and artifact digest; log the resolved method, path, target, parameters, principal, approval ID, task ID, and result.

## Initial safe operation allowlist

Begin with GET-only observation. The API viewer is the source of truth for exact endpoint schemas and required privileges. ([API viewer](https://pve.proxmox.com/pve-docs/api-viewer/))

| Purpose | Allow initially | Conditions |
|---|---|---|
| API and cluster health | `GET /version`, `GET /cluster/status` | Return only the fields needed for health and version checks. |
| Bounded inventory | `GET /cluster/resources?type=vm`, `GET /nodes` | Filter responses to the approved pool and node set before they reach the model. |
| Node status | `GET /nodes/{node}/status`, `GET /nodes/{node}/storage` | `{node}` must be in a static allowlist; expose capacity and status, not arbitrary logs. |
| Guest status | `GET /nodes/{node}/qemu/{vmid}/status/current`, `GET /nodes/{node}/lxc/{vmid}/status/current` | `{vmid}` must belong to the approved resource pool. |
| Snapshot inventory | `GET /nodes/{node}/qemu/{vmid}/snapshot`, `GET /nodes/{node}/lxc/{vmid}/snapshot` | List metadata only; no create, delete, or rollback. |
| Approved task observation | `GET /nodes/{node}/tasks/{upid}/status` | Permit only a task ID returned by an already approved operation; do not allow arbitrary task-log browsing. |

Do not initially expose guest configuration, cloud-init data, arbitrary logs, storage content, ACLs, token management, console access, guest-agent file access, a raw API passthrough, or any POST, PUT, or DELETE request. Read-only access can still disclose sensitive operational data, so response filtering belongs in the adapter as well as in RBAC.

## Human-gated operations

At the start, require a human approval for every mutation. Keep these API and host-level operation categories permanently gated. ([API viewer](https://pve.proxmox.com/pve-docs/api-viewer/), [pvesh manual](https://pve.proxmox.com/pve-docs/pvesh.1.html))

- guest, container, snapshot, backup, volume, storage, user, token, role, ACL, firewall, SDN, HA, replication, or cluster deletion;
- snapshot rollback, backup restore, backup pruning, disk initialization, disk or volume move, and disk resize;
- hard stop, reset, suspend, reboot, node power management, service restart, task cancellation, and every bulk action;
- migration, template conversion, cluster join, HA or replication changes, network changes, firewall changes, storage changes, and package updates;
- guest-agent command execution, guest file read or write, password changes, console access, shell access, SSH, and `pvesh`;

Keep creation or cloning of guests, containers, storage, users, tokens, roles, firewall rules, and scheduled jobs human-gated until each has a separately reviewed bounded workflow.

An approval should bind to the exact operation, target IDs, parameters, expected current state, expiry, and a single-use nonce. The review screen should show the proposed diff, affected guests or nodes, expected interruption, backup or rollback evidence, and postcondition checks. Reject an approval if the state changes before execution. Record the request and result outside the agent's write access.

## Staged recommendation

1. **Observe through the direct API.** Deploy the adapter with only the GET allowlist and a privilege-separated read token. Prove that intended reads succeed and that representative POST, PUT, and DELETE calls fail at Proxmox RBAC even if the adapter is bypassed.
2. **Add one bounded write workflow in a test pool.** Use a separate write token and one-time human approval. Start with a reversible, single-guest action such as creating a snapshot or starting a designated test guest. Exercise token revocation, approval expiry, stale-state rejection, audit-log integrity, and recovery before adding another workflow.
3. **Pilot MCP only if it improves operator experience.** Evaluate Proximo first for its recorded plans and opt-in out-of-band consent, with SSH/exec disabled and consent state outside the agent's write reach; do not treat caller-supplied `confirm=True` as human approval. Evaluate Samik081/mcp-pve in `read-only` mode with no force-included tools. Evaluate GethosTheWalrus/proxmox-mcp with read-only enabled, raw API disabled, TLS verification enabled, and a non-root user. In every case, keep the same external broker, endpoint allowlist, and Proxmox token boundary. ([Proximo dispatch](https://raw.githubusercontent.com/john-broadway/proximo/main/src/proximo/server.py), [Proximo security model](https://github.com/john-broadway/proximo/blob/main/SECURITY.md), [mcp-pve](https://github.com/Samik081/mcp-pve), [proxmox-mcp](https://github.com/GethosTheWalrus/proxmox-mcp))
4. **Promote workflows, not general authority.** Add one operation at a time after a recovery drill and policy review. Keep destructive actions human-gated and keep SSH/root paths outside the AI runtime.

This design preserves a clean exit: removing or replacing the MCP adapter does not change credentials, RBAC, approvals, or the audit model. Proxmox remains the authority; MCP remains transport.

## Primary sources

- [Proxmox VE API overview](https://pve.proxmox.com/wiki/Proxmox_VE_API)
- [Proxmox VE API viewer](https://pve.proxmox.com/pve-docs/api-viewer/)
- [`pveum(1)` user, token, role, and ACL reference](https://pve.proxmox.com/pve-docs/pveum.1.html)
- [`pvesh(1)` reference](https://pve.proxmox.com/pve-docs/pvesh.1.html)
- [Proxmox `pve-apiclient` mirror](https://github.com/proxmox/pve-apiclient)
- [john-broadway/proximo](https://github.com/john-broadway/proximo)
- [Samik081/mcp-pve](https://github.com/Samik081/mcp-pve)
- [GethosTheWalrus/proxmox-mcp](https://github.com/GethosTheWalrus/proxmox-mcp)
