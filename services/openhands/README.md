# OpenHands Agent Canvas — self-hosted agent backend

All-in-one OpenHands Agent Canvas (agent server + automation backend + web
frontend) for a trusted-LAN/VPN or local install. This package is a
**single-tenant evaluation backend**: conversations persist on the host,
agents execute **inside this container**, and the web UI requires the
backend API key. No GitHub/Slack automation credentials, no ACP agent
credentials, and no per-conversation sandboxing are configured by this
stack.

## Images and requirements

| Service | Image | Architectures | Limits |
|---|---|---|---|
| `openhands` | `ghcr.io/openhands/agent-canvas:1.24.0@sha256:ad0829a7082a71ddfd2d16c1fae5a2172e4ca5a34eba7f03b69bd5b9b1bc54d7` | linux/amd64, linux/arm64 (multi-arch index digest) | 4G RAM, 2.0 CPUs |

- Upstream: OpenHands **v1.24.0** (released 2026-09-25). Canvas and the
  automation backend are upstream-labeled **beta**; expect interface churn
  across upgrades and re-check the pinned digest when bumping.
- The image runs as `openhands` (UID/GID **10001**) under `tini` with the
  upstream entrypoint. Do not add `init: true`, override the entrypoint, or
  force `user:`. Unlike the paperclip image there is **no root
  ownership-repair phase**: the bind-mounted `state/` and `projects/`
  directories must already be owned by UID/GID 10001 before first start
  (see the install sections).
- Unified entry point is container port **8000**; the web UI is served
  under **`/canvas`**. The healthcheck probes `/alive` using the image's
  bundled python3.
- Single replica only. Conversation history, settings, encrypted secrets,
  the session API key, and the automation SQLite DB all live in one shared
  `state/` tree. Never point a second writer at the same directories.
- The image pre-creates `/home/openhands/.openhands` and `/projects` as
  VOLUMEs; both are bind-mounted here so data survives recreation.

## Scope and security boundary

- **HTTP only**, accepted solely on a trusted LAN/VPN. No TLS, reverse
  proxy, or SSO layer is added by this stack.
- **Single-tenant.** One backend API key (`X-Session-API-Key`) gates every
  API call; the UI prompts for it on first load (public mode — the key is
  not baked into the served HTML when the port is published beyond
  loopback). There is no per-user auth, RBAC, or tenant isolation: anyone
  on the LAN holding the key drives the agents.
- **Shared trusted execution.** Agents run inside this one container with
  its filesystem, environment, and network reach (LAN plus the model
  gateway). This is the deliberate "shared trusted first" evaluation
  shape; it is **not** a sandbox boundary between projects, nor between
  the agent and its own state. Do not mount the Docker socket, host
  credentials, or other services' data into it.
- The bundled OpenVSCode editor is served from the same origin under
  `/vscode`; script running on that origin can read Canvas's localStorage
  session keys (upstream issue #16492). Keep the URL LAN/VPN-only and do
  not browse untrusted content in it.
- Telemetry is disabled: `VITE_DO_NOT_TRACK=1` suppresses the bundled
  PostHog key in the frontend, automation backend, and agent server.
- Nothing model-facing works until an LLM profile is configured (below).
  The stack boots healthy with zero model credentials.

## Configuration

Create a `.env` next to `docker-compose.yml` (git-ignored) or supply the
values through Portainer's stack Env array. Blank optional values keep their
upstream behavior.

| Key | Default | Notes |
|---|---|---|
| `OPENHANDS_DATA_DIR` | *(required, blank fails interpolation)* | Absolute writable path **outside the checkout**; holds `state/` and `projects/`. TrueNAS: `/mnt/tank/container-configs/openhands`. Local: `$HOME/.local/share/openhands` (expand `$HOME` when writing it). |
| `OPENHANDS_BIND_IP` | `127.0.0.1` | Host interface for the UI port; use the LAN address for trusted-LAN installs. |
| `OPENHANDS_PORT` | `3200` | Host port (container port is 8000). |
| `OPENHANDS_PUBLIC_URL` | *(empty)* | Externally reachable URL (e.g. `http://192.168.1.39:3200`) used for automation callback URLs; empty keeps the upstream internal default. |
| `OPENHANDS_BACKEND_API_KEY` | *(empty)* | The Canvas/backend access key. **Empty is fine**: first boot generates one and persists it to `state/agent-canvas/api-key.txt`. Set your own (e.g. `openssl rand -base64 32`) to pin it; changing it later rotates access for every browser. |
| `OPENHANDS_LITELLM_BASE_URL` | *(empty)* | Optional LLM bootstrap: bare LiteLLM proxy URL, e.g. `http://192.168.1.98:4000` (upstream docs show no `/v1` suffix for the `litellm_proxy/` provider). |
| `OPENHANDS_LITELLM_MODEL` | *(empty)* | Optional LLM bootstrap: `litellm_proxy/<model-id>` as served by the gateway, e.g. `litellm_proxy/swift-1.5-awq`. |
| `OPENHANDS_LITELLM_API_KEY` | *(empty)* | Optional LLM bootstrap: scoped LiteLLM key. Never the LiteLLM master key. |

Only `OPENHANDS_DATA_DIR` is a hard requirement; every other value has a
safe default.

## First login

1. Open the UI at `http://<bind-ip>:<port>/canvas`.
2. Enter the backend API key when prompted. If `OPENHANDS_BACKEND_API_KEY`
   was left empty, retrieve the generated value from
   `state/agent-canvas/api-key.txt` (container console:
   `cat /home/openhands/.openhands/agent-canvas/api-key.txt`) — it is
   deliberately never printed to container logs or chat.
3. The same key authenticates all backends (agent server + automation).

## Model setup (LiteLLM)

The **documented, validated path** is the Canvas UI:

1. `Settings > LLM` → enable **Advanced**.
2. Custom Model: `litellm_proxy/<model-id>` (e.g. `litellm_proxy/swift-1.5-awq`).
3. Base URL: the bare LiteLLM proxy URL (e.g. `http://192.168.1.98:4000`).
4. API Key: a scoped LiteLLM key. Save — the backend validates the profile
   against the gateway before persisting, and stores it encrypted with the
   auto-generated `OH_SECRET_KEY` (`state/agent-canvas/secret-key.txt`).

The `OPENHANDS_LITELLM_*` stack variables are an optional pass-through
bootstrap (the upstream Helm chart documents `LLM_MODEL`/`LLM_API_KEY` the
same way). If both are set, check `Settings > LLM` to see which
configuration is live. **Preserve `state/` across redeploys** — it holds
the encryption key for saved LLM keys, the session key, conversation
history, and the automation database; losing it breaks every saved secret.

## Local install (work/home workstation)

```sh
mkdir -p "$HOME/.local/share/openhands/state" "$HOME/.local/share/openhands/projects"
sudo chown -R 10001:10001 "$HOME/.local/share/openhands"
```

From `services/openhands/` with a filled `.env` (`chmod 600 .env`):

```sh
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --wait --wait-timeout 300
```

The root `.gitignore` already protects `.env`; this file must never receive
real credentials. The UID 10001 chown is required because the image has no
root ownership-repair phase.

## TrueNAS install (GitOps through Portainer CE)

Create only these directories (no recursive permission changes to the
parent):

```sh
ssh truenas 'mkdir -p /mnt/tank/container-configs/openhands/state /mnt/tank/container-configs/openhands/projects'
```

Then hand ownership to the container's UID **once** (root on the host, or
the equivalent one-shot through Portainer's Docker API when SSH lacks the
docker group):

```sh
docker run --rm \
  -v /mnt/tank/container-configs/openhands/state:/s \
  -v /mnt/tank/container-configs/openhands/projects:/p \
  alpine:3.22 chown -R 10001:10001 /s /p
```

Portainer stack `openhands` on the `truenas` environment, repository
`https://github.com/mspiegel31/home-services`, ref `refs/heads/main`,
compose path `services/openhands/docker-compose.yml`, with this `Env`
array:

```dotenv
OPENHANDS_DATA_DIR=/mnt/tank/container-configs/openhands
OPENHANDS_BIND_IP=192.168.1.39
OPENHANDS_PORT=3200
OPENHANDS_PUBLIC_URL=http://192.168.1.39:3200
OPENHANDS_BACKEND_API_KEY=
OPENHANDS_LITELLM_BASE_URL=http://192.168.1.98:4000
OPENHANDS_LITELLM_MODEL=litellm_proxy/swift-1.5-awq
OPENHANDS_LITELLM_API_KEY=
```

`OPENHANDS_LITELLM_API_KEY` is intentionally left empty at deploy time:
paste the scoped LiteLLM key into the stack environment in the Portainer
UI and update the stack, and/or enter it once under `Settings > LLM` in the
Canvas UI. After changing any stack value, redeploy from the updated ref
(`StackGitRedeploy` or the UI's update action) and confirm the stack's
config hash advanced.

The UI is then at `http://192.168.1.39:3200/canvas`.

## Upgrades and recovery

- Bump the pinned tag + digest in the repo, commit, push, then redeploy
  from `main` through Portainer. `state/` and `projects/` survive
  recreation; live agent processes do not — interrupting a running
  conversation mid-task is expected during a redeploy.
- Never use volume/data deletion as a troubleshooting step, and never
  `down -v`.
- Back up `state/` and `projects/` with the rest of
  `container-configs`; `state/` contains material that cannot be
  regenerated (encryption key, session key, conversation history,
  automation DB).
