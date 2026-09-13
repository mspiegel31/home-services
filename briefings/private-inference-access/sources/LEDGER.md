# Source ledger

Every row records a source read for the draft. The `repoEvidence2026` row points to the durable, sanitized repository excerpts that remain after consolidation sources are removed.

| key | url | fetched | summary |
|-----|-----|---------|---------|
| repoEvidence2026 | `sources/evidence.json` | 2026-09-09 | Revision-pinned local plan and configuration provenance, with no secret values. |
| pangolinArchitecture2026 | <https://docs.pangolin.net/development/system-architecture> | 2026-09-09 | Control plane, node roles, public and private paths, outbound sites, and WireGuard relay behavior. |
| pangolinHttp2026 | <https://docs.pangolin.net/manage/resources/public/http-https> | 2026-09-09 | Public FQDN, node-side TLS termination, authentication, and target forwarding. |
| pangolinPublicAI2026 | <https://docs.pangolin.net/manage/resources/public/ai-gateway> | 2026-09-09 | Public AI Gateway key checks, provider routing, and authentication behavior. |
| pangolinProviderConfig2026 | <https://docs.pangolin.net/manage/ai/providers/configuration> | 2026-09-09 | Upstream authentication, key stripping, identity headers, target modes, and TLS controls. |
| pangolinSessionLogs2026 | <https://docs.pangolin.net/manage/ai/session-logs> | 2026-09-09 | Transcript contents, edition availability, default retention, and export behavior. |
| pangolinRemoteNodes2026 | <https://docs.pangolin.net/manage/remote-node/understanding-nodes> | 2026-09-09 | Remote-node data plane, cloud control plane, optional cloud failover, and AI Gateway restriction. |
| pangolinNewtConfig2026 | <https://docs.pangolin.net/manage/sites/configure-site> | 2026-09-09 | Newt credential precedence, health file, cloud-failover switch, Docker discovery, and network validation. |
| pangolinSelfHost2026 | <https://docs.pangolin.net/self-host/quick-install> | 2026-09-09 | Self-host prerequisites, listener ports, installer flow, and initial administration. |
| pangolinPrivateHttp2026 | <https://docs.pangolin.net/manage/resources/private/private-http> | 2026-09-09 | Client-only private HTTP path and TLS termination at the site connector. |
| pangolinRaw2026 | <https://docs.pangolin.net/manage/resources/public/raw-resources> | 2026-09-09 | Raw public TCP/UDP reachability, lack of Pangolin authentication, and host-port requirements. |
| cloudflareProtocols2026 | <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/protocols/> | 2026-09-09 | Published protocol matrix and client-side cloudflared requirement for non-HTTP services. |
| cloudflareTlsModes2026 | <https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/> | 2026-09-09 | Separate visitor-to-Cloudflare and Cloudflare-to-origin TLS connections. |
| cloudflarePrivacy2025 | <https://www.cloudflare.com/privacypolicy/> | 2026-09-09 | Current policy on end-user traffic processing and purpose-based retention. |
| cloudflarePrivacy2021 | <https://cf-assets.www.cloudflare.com/slt3lc6tev37/7LWVoYkDCeA0LlEaGyMQtS/5a7a45572bed7f192f6d4de2b26876cd/How_the_Cloudflare_network_maintains_data_privacy.pdf> | 2026-09-09 | Dated whitepaper describing request inspection and sampled HTTP traffic retention up to 12 months. |
| cloudflaredIssue1654 | <https://github.com/cloudflare/cloudflared/issues/1654> | 2026-09-09 | Open community request for browser-direct, connector-blind TLS pass-through; not vendor documentation. |
| digitaloceanMarketplace2026 | <https://marketplace.digitalocean.com/apps/pangolin-ce-1> | 2026-09-09 | Marketplace publisher, image, operating system, and currently listed package versions. |
| digitaloceanDroplets2026 | <https://docs.digitalocean.com/products/droplets/> | 2026-09-09 | Droplets as Linux virtual machines on DigitalOcean virtualized hardware. |
| dockerRestart2026 | <https://docs.docker.com/engine/containers/start-containers-automatically/> | 2026-09-09 | Restart policies act when containers exit or the daemon restarts. |
| litellmSecurity2026 | <https://docs.litellm.ai/docs/proxy/security_best_practices> | 2026-09-09 | Private-network guidance, TLS, virtual keys, secret storage, and trusted reverse-proxy settings. |
