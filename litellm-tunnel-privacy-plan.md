# LiteLLM over Pangolin — Opaque-Privacy Plan

Status: ready for implementation
Date: 2026-08-28
Amended 2026-08-28: Cloudflare Tunnel TCP route + per-host Traefik (LE DNS-01)
**rejected**; tunnel technology slot replaced with **Pangolin** (node on a DigitalOcean
VPS + Newt site connector on the home box).

## TL;DR

Expose LiteLLM to the internet through a **Pangolin** node on a DigitalOcean VPS,
with a **Newt** site connector on the home box. The client (any browser or OpenAI-
compatible SDK) dials a public FQDN with zero client software installed; Pangolin's
node on the VPS terminates TLS and enforces auth, then relays the request over an
outbound WireGuard tunnel (Newt) to LiteLLM on the home box. Because the TLS-
terminating **data plane is the user's own VPS**, prompts/completions/API keys never
transit a third party, and the home WAN IP is not the public endpoint. LiteLLM stays
the AI layer (authn, thinking-policy callback, model routing to llama-swap); Pangolin
is the tunnel/ingress, not a replacement for it.

**Chosen mode: self-hosted CE on the VPS** (deployed via the DigitalOcean "Pangolin
(CE)" 1-Click). This is the only mode where Pangolin's **AI Gateway** can route to the
home box, and it involves no third party at all. The "Remote Node" (Pangolin Cloud
control plane + VPS node) fallback is documented below.

## Why not Cloudflare Tunnel

The original plan used a Cloudflare Tunnel **TCP route** so the Cloudflare edge would
be structurally blind to the TLS handshake. After research, that was rejected:

- **Browser-direct blind TLS pass-through over Tunnel is not implemented.** The feature
  (cloudflared#1654) is still open. The only ways to get an opaque L4 relay through
  Cloudflare today require a **client-side `cloudflared access tcp` binary** plus a
  per-laptop **DNS override** (`/etc/hosts` / Tailscale split-DNS / a local resolver)
  so the public hostname resolves to the local relay. That is per-device client
  software + DNS trickery — the exact friction this stack set out to avoid.
- **The L7 (HTTP) route is not private.** The Cloudflare edge terminates TLS and, per
  Cloudflare's privacy whitepaper, retains a **sampled copy of HTTP traffic for up to
  12 months**. That is a documented third-party retention of the LLM data path —
  unacceptable for prompts/completions/API keys.
- **Traefik DDoS research**: direct `:443` exposure is a real DDoS target, and the
  per-host Traefik pattern only offloads the volumetric flood (via Cloudflare) — it does
  not make the edge blind. The privacy property requires the edge to hold no key.

**Decision:** use a tunnel technology where the user's **own** box terminates TLS and
holds the key. Pangolin does exactly that (the node is the TLS endpoint; Newt is a
deny-by-default proxy to the backend), the client is browser/SDK-direct with zero
software, and the home box has no public IP.

## Architecture

### Data path

```
client (any browser / OpenAI-compatible SDK, zero software)
  -> llm.electricgarage.net  (public FQDN; resolves to the DO VPS)
  -> Pangolin node on the DO VPS  (TLS terminates HERE — user's box)
       - Gerbil: WireGuard tunnel manager
       - Traefik: ingress / TLS / cert routing
       - Badger: forward-auth middleware (enforces virtual key / SSO)
       - control plane (Mode B: self-hosted; Mode A: Pangolin Cloud)
  -> WireGuard tunnel (Gerbil <-> Newt)
  -> Newt site connector on the home box  (outbound, no public IP, deny-by-default)
  -> LiteLLM :4000  ->  llama-swap :11437  ->  vLLM backends
```

### Key properties

- **Zero client software.** Browser/SDK dial the public FQDN over HTTPS. No
  `cloudflared access tcp`, no `/etc/hosts`, no per-laptop DNS override.
- **No home IP exposure.** The public endpoint is the VPS IP. The home box's WAN IP
  (`107.5.206.99`, the existing WireGuard A record) stays as-is for the separate
  WireGuard tunnel and is not the LLM endpoint.
- **Content stays on the user's VPS.** The TLS-terminating node (data plane) runs on the
  user's VPS. In the chosen Mode B nothing leaves the VPS. In Mode A the data plane is
  still the VPS; only control-plane *metadata* (identity, policies, DNS, certs,
  telemetry) goes to Pangolin Cloud — never traffic content.
- **LiteLLM stays the AI layer.** Thinking-policy callback, model routing to llama-swap,
  and virtual keys are all unchanged.
- **llama-swap/vLLM never exposed.** Only reachable from LiteLLM over the internal
  `litellm` docker network, and from Newt's deny-by-default proxy. No new inbound port
  on the home box (Newt is outbound).

## Deployment modes

Two ways to run the node. **The DO 1-Click app the user named deploys Mode B
(self-hosted CE)**, which is also the mode that unlocks the AI Gateway — so B is the
chosen path. A is documented as the lower-maintenance fallback if the user later
prefers the managed control plane.

### Mode B — Self-hosted CE on the VPS  (CHOSEN)

- **What runs on the VPS:** the full Pangolin stack — control plane (dashboard, identity,
  policy, DNS, cert issuance) **and** the node (Gerbil + Traefik + Badger), plus its DB.
- **AI Gateway:** works pointing at the home box (the server node *is* the VPS), so
  per-device virtual API keys, prompt/response session logs, token/USD budgets, and usage
  analytics are all available on the LLM path.
- **Third-party involvement:** none. No Pangolin Cloud, no Fossorial service in any path.
- **Cost:** the user owns the control plane + DB (updates, migrations, backups). The DO
  1-Click app (image `fossil/pangolince1`, Ubuntu 24.04, min 1 vCPU / 1 GB) does the
  initial install; ongoing operation is the user's.

### Mode A — Remote Node (Pangolin Cloud control plane + VPS node)  (fallback)

- **What runs on the VPS:** the node only (Gerbil + Traefik + Badger + agent). Handles
  TLS, tunnel, relay.
- **What Pangolin Cloud manages:** control plane (dashboard, DNS, cert issuance,
  coordination, identity).
- **What Pangolin Cloud sees:** control-plane *metadata* only — identity, access
  policies, DNS records, certs, telemetry (connection/relay state). **Never traffic
  content** (the data plane stays on the VPS).
- **Limitation:** Pangolin's **AI Gateway cannot route to a site attached to a remote
  node** — AI Gateway providers only target the Pangolin *server* node, and DNS
  resolution of gateway resources never points at remote nodes. So on Mode A you get the
  tunnel + auth + access control + dashboard + multi-site, but **not** the AI Gateway
  features (virtual keys / session logs / budgets) on the LLM path; LiteLLM remains the
  sole AI layer.
- **Use when:** the user prefers the managed control plane and is fine keeping LiteLLM
  as the AI brain. Lower operational burden.

### Mode comparison

| | Mode B (self-hosted CE)  (chosen) | Mode A (Remote Node) |
|---|---|---|
| Runs on the VPS | control plane + node + DB | node only |
| Control plane | the VPS (user-owned) | Pangolin Cloud |
| AI Gateway → home box | **Yes** | **No** (server-node-only routing) |
| AI session logs / budgets / virtual keys | Yes | No (LiteLLM handles keys only) |
| Third party in any path | **None** | Pangolin Cloud (metadata only, never content) |
| Ops burden | Higher (own the control plane + DB) | Lower (cloud handles DNS/certs/coord) |
| DO deploy | "Pangolin (CE)" 1-Click | plain Ubuntu droplet + node installer |

## VPS provisioning (DigitalOcean)

- **Provider:** DigitalOcean.
- **Mode B (chosen):** deploy the **"Pangolin (CE)" 1-Click App** from the DO Marketplace
  (publisher: Fossorial; image slug `fossil/pangolince1`; Ubuntu 24.04). Recommended
  sizing: 1 vCPU / 1 GB minimum — the node is a WireGuard manager + Traefik + auth
  middleware, not a compute workload. Point the LLM FQDN at the droplet IP (or a
  Pangolin-managed subdomain).
- **Mode A (fallback):** a plain Ubuntu 24.04 droplet (same sizing), open firewall ports
  `80/tcp`, `443/tcp`, `51820/udp`, `21820/udp` (clients), then run Pangolin's remote-node
  installer:
  ```bash
  curl -fsSL https://static.pangolin.net/get-node-installer.sh | bash
  sudo ./installer
  ```
  The installer generates node credentials to adopt in the Pangolin Cloud dashboard
  (Self-hosted → add node → adopt).
- **Domain:** the domain is `electricgarage.net`. The LLM FQDN is a subdomain, e.g.
  `llm.electricgarage.net` (or a Pangolin-assigned subdomain if using Pangolin's DNS).
  In Mode B the user creates the CNAME in their Cloudflare zone; in Mode A Pangolin
  Cloud manages the subdomain.

## What is NEW in the repo

### `services/pangolin-newt/`

A small Docker container on the **home box** that:
- Opens an **outbound** WireGuard tunnel to the Pangolin node on the VPS (no inbound
  ports, no home IP exposure).
- Acts as a **deny-by-default** proxy to the backend target (LiteLLM) — Newt only
  forwards what Pangolin authorizes.

Files:
- `docker-compose.yml` — the Newt container (image `fosrl/newt`), wired into the `litellm`
  docker network so it can reach `litellm:4000`, with a healthcheck on Newt's health file.
- `AGENTS.md` — what it is, the secrets needed (via Portainer env vars, never committed),
  how it connects to the Pangolin node, and how to point the public resource at LiteLLM.

**Secrets (Portainer UI, never committed):**
- `NEWT_ID` — site ID from the Pangolin dashboard.
- `NEWT_SECRET` — site secret (keep private; used for websocket auth).
- `PANGOLIN_ENDPOINT` — the VPS's Pangolin endpoint (Mode B: the VPS FQDN, e.g.
  `https://pangolin.electricgarage.net`; Mode A: `https://app.pangolin.net`).

**Newt config notes (verified from fosrl/newt):**
- Env vars `NEWT_ID`, `NEWT_SECRET`, `PANGOLIN_ENDPOINT` (CLI flags or config file also
  supported; precedence: CLI > env > config file).
- `DOCKER_SOCKET=/var/run/docker.sock` enables container discovery so Newt can address
  the `litellm` container as a target without hard-coding an IP. `DOCKER_ENFORCE_NETWORK_VALIDATION=true`
  then requires the target to be on Newt's network (useful hardening).
- `HEALTH_FILE=/tmp/healthy` + a compose healthcheck lets Docker restart Newt if the
  tunnel drops.
- No `ports:` — Newt is outbound only.

### `services/pangolin-newt/docker-compose.yml` (draft, verify against live Newt)

```yaml
# Pangolin Newt site connector (home box)
# Outbound WireGuard tunnel to the Pangolin node on the DO VPS; deny-by-default
# proxy to LiteLLM. No inbound ports. Portainer CE stack:
#   repo https://github.com/mspiegel31/home-services.git, ref main,
#   path services/pangolin-newt/docker-compose.yml, poll 5 min.
#
# Secrets via Portainer UI (never commit):
#   NEWT_ID, NEWT_SECRET, PANGOLIN_ENDPOINT

name: pangolin-newt

services:
  newt:
    container_name: pangolin-newt
    image: fosrl/newt:latest   # [VERIFY] pin a specific tag for production
    restart: unless-stopped
    environment:
      - PANGOLIN_ENDPOINT=${PANGOLIN_ENDPOINT:?Set PANGOLIN_ENDPOINT in Portainer}
      - NEWT_ID=${NEWT_ID:?Set NEWT_ID in Portainer}
      - NEWT_SECRET=${NEWT_SECRET:?Set NEWT_SECRET in Portainer}
      - DOCKER_SOCKET=/var/run/docker.sock
      - DOCKER_ENFORCE_NETWORK_VALIDATION="true"
      - HEALTH_FILE=/tmp/healthy
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD-SHELL", "[ -f /tmp/healthy ]"]
      interval: 30s
      timeout: 5s
      start_period: 30s
      retries: 3
    # No ports: Newt is outbound-only (WireGuard + websocket to the node).
    networks:
      - litellm   # join the litellm network so Newt can target litellm:4000

volumes: {}

networks:
  litellm:
    external: true          # the network created by services/litellm/docker-compose.yml
```

> **Joining the `litellm` network:** the litellm stack declares a top-level `networks:
> litellm:` (name `litellm`). For Newt to reach `litellm:4000` it must be on that same
> network. On Portainer (multi-stack), the cleanest approach is to put Newt in the same
> `litellm` stack/compose file, or reference the network as `external: true` as above
> (the network already exists by name `litellm`). **Verify the network name matches** what
> the litellm stack creates before deploying.

### `services/pangolin-newt/AGENTS.md` (draft)

```markdown
# Pangolin Newt (home box site connector)

Outbound WireGuard tunnel to the Pangolin node on the DigitalOcean VPS, and a
deny-by-default proxy to LiteLLM. No inbound ports; the home box has no public IP.

## Flow

client -> llm.electricgarage.net -> Pangolin node (DO VPS, TLS + auth) ->
WireGuard (Newt) -> this container -> litellm:4000 -> llama-swap -> vLLM

## Secrets (Portainer UI, never commit)

- NEWT_ID / NEWT_SECRET: site credentials from the Pangolin dashboard.
- PANGOLIN_ENDPOINT: the VPS Pangolin endpoint (Mode B: VPS FQDN; Mode A:
  https://app.pangolin.net).

## Notes

- Image: fosrl/newt. Pin a tag for production.
- DOCKER_SOCKET + DOCKER_ENFORCE_NETWORK_VALIDATION=true let Newt address the
  litellm container as a target and require it to be on Newt's network.
- HEALTH_FILE drives the compose healthcheck (restarts Newt if the tunnel drops).
- The public resource in the Pangolin dashboard targets litellm:4000 on this site.
```

## What stays unchanged (do NOT modify)

- `services/litellm/docker-compose.yml` — LiteLLM stack unchanged. Port 4000 stays
  internal (reachable from Newt over the `litellm` network, not public).
- `services/litellm/config.yaml` — unchanged.
- `services/litellm/custom_callbacks.py` — unchanged (Qwen3.8 thinking policy).
- `services/llama-swap-vllm/` — unchanged. llama-swap remains the backend scheduler.
- `services/cloudflared/docker-compose.yml` — **unchanged** for the existing
  orange-cloud apps (immich, plex, openwebui, searxng, etc.). Only the **LLM path** moves
  to Pangolin. The existing cloudflared tunnel stays for non-LLM apps where the L7 trade
  is accepted.
- No `services/traefik/` — Pangolin's node includes Traefik; no per-host Traefik needed.

## Manual steps (user does — not in the repo)

**Mode B (chosen):**

1. **Deploy the VPS:** DigitalOcean Marketplace → "Pangolin (CE)" 1-Click App → create a
   droplet (1 vCPU / 1 GB, pick region). Note the droplet IP.
2. **Create the Pangolin org / log in** to the CE dashboard on the VPS (the 1-Click sets
   this up; you'll get the admin URL — typically the VPS FQDN or IP on 443).
3. **Create a Site** for the home box; copy the **Newt config** (ID + secret + endpoint).
4. **Create a public resource** (HTTP/HTTPS, or an AI Gateway resource if using the AI
   layer) pointing at the home-box site, target `litellm:4000`. Enable auth (virtual API
   key and/or SSO).
5. **DNS:** in the Cloudflare zone, create `llm.electricgarage.net` → CNAME to the VPS's
   Pangolin hostname (or A to the droplet IP if self-terminating). For the AI Gateway /
   resource subdomains, follow the subdomain Pangolin assigns.
6. **Deploy Newt** on the home box: add a Portainer CE stack from
   `services/pangolin-newt/docker-compose.yml`; set `NEWT_ID`, `NEWT_SECRET`,
   `PANGOLIN_ENDPOINT` in Portainer.
7. **Create a virtual API key** (and/or SSO account) in Pangolin for each client.
8. **Point clients at the FQDN** (`https://llm.electricgarage.net`) with the virtual key.

**Mode A (fallback):** steps 1-2 become: provision a plain Ubuntu droplet, run the node
installer, and adopt the node in the **Pangolin Cloud** dashboard (app.pangolin.net).
Pangolin Cloud then manages DNS/subdomains (skip step 5). AI Gateway is unavailable for
the home-box target (see Mode A limitation).

## Verification (do all)

1. **TLS terminates on the VPS:** from a client,
   `openssl s_client -connect llm.electricgarage.net:443 -servername llm.electricgarage.net`
   → clean verify; cert issued by the expected CA (Let's Encrypt or Pangolin's CA), SAN
   matches the FQDN.
2. **Auth enforced:** with **no** valid virtual key / SSO session, requests to the FQDN
   are rejected by Badger (401/403) before reaching LiteLLM.
3. **End-to-end:** one chat completion through the OpenAI SDK from a laptop using the
   virtual key; confirm llama-swap served it and LiteLLM logs show the request.
4. **No home IP exposure:** the FQDN resolves to the **VPS IP**, not the home WAN IP.
   `nc -zv <home-wan-ip> 4000` refuses (loopback/internal only). The home box's
   `107.5.206.99` is reachable only for the separate WireGuard tunnel (UDP 51820).
5. **Content stays on the VPS:**
   - Mode B: confirm no outbound connections from the VPS other than to the home box's
     Newt tunnel and (none, since self-hosted) — no third-party egress for LLM traffic.
   - Mode A: confirm in the Pangolin Cloud dashboard that only metadata/telemetry is
     recorded, no traffic content.
6. **Newt health:** `docker exec pangolin-newt test -f /tmp/healthy && echo OK` returns
   OK; the compose healthcheck is healthy.
7. **Existing apps unaffected:** the orange-cloud apps (immich, plex, etc.) still work
   through the existing cloudflared tunnel.

## Operational notes

- **VPS sizing:** 1 vCPU / 1 GB is the floor; the node is lightweight. Scale up only if
  the VPS also hosts heavy workloads.
- **Updates:** Mode B — the user updates Pangolin on the VPS (the 1-Click does not auto-
  patch the control plane). Newt on the home box updates via the `fosrl/newt` image tag.
- **If the VPS goes down:** the LLM path is unavailable (the VPS is the only public
  endpoint and the tunnel hub). The home box itself keeps running; llama-swap/vLLM and
  the LAN are unaffected. Restore by re-provisioning the droplet and re-adopting /
  re-pointing DNS.
- **Failover (optional):** a second node in another region/region can take over; Pangolin
  supports multiple nodes. Not required for a single-VPS home setup.
- **Cert renewal:** Pangolin manages cert issuance for the resource subdomains (Mode B:
  via its ACME; Mode A: via Pangolin Cloud). No per-host ACME wiring in the repo.

## Accepted caveats

- **llama-swap/vLLM never exposed.** Newt is deny-by-default; only the LiteLLM target
  authorized in the public resource is reachable. No new inbound port on the home box.
- **Master key stays in Portainer.** `LITELLM_MASTER_KEY` is set in Portainer, never
  committed. Pangolin presents the client's virtual key / SSO identity to LiteLLM.
- **One virtual key per client** (Mode B AI Gateway or LiteLLM virtual keys) for clean
  per-device attribution and spend tracking.
- **Mode A metadata caveat (if the fallback is used):** Pangolin Cloud sees control-plane
  metadata (identity, policies, DNS, certs, telemetry), never content. The chosen Mode B
  avoids even that.

## Sources

- Pangolin system architecture (control plane / node / Newt / Gerbil / Badger, data flow):
  <https://docs.pangolin.net/development/system-architecture>
- Pangolin Remote Nodes (data plane stays on your server; AI Gateway routing limitation):
  <https://docs.pangolin.net/manage/remote-node/understanding-nodes>
- Pangolin Remote Node quick install (installer + ports 80/443/51820/21820):
  <https://docs.pangolin.net/manage/remote-node/quick-install-remote>
- Newt install (binary/Docker, `fosrl/newt`, env vars, healthcheck, Portainer):
  <https://docs.pangolin.net/manage/sites/install-site>
- Newt configure (flags/env/config-file precedence, DOCKER_SOCKET, HEALTH_FILE):
  <https://docs.pangolin.net/manage/sites/configure-site>
- Newt repo: <https://github.com/fosrl/newt>
- DigitalOcean "Pangolin (CE)" 1-Click App (publisher Fossorial, image `fossil/pangolince1`):
  <https://marketplace.digitalocean.com/apps/pangolin-ce-1>
- Cloudflare Tunnel "blind TLS pass-through" feature request (proof L7/L4 isn't blind today):
  <https://github.com/cloudflare/cloudflared/issues/1654>
- Cloudflare privacy / data-retention (sampled HTTP traffic retained up to 12 months):
  <https://www.cloudflare.com/trust/resources/privacy/>
- LiteLLM security best practices (master key, virtual keys, private networks):
  <https://docs.litellm.ai/docs/proxy/security_best_practices>
