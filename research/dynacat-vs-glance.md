# Dynacat 3.0 vs. Glance: Evaluation Report

**Date:** 2026-09-12
**Scope:** Whether to switch the local Glance deployment to Panonim/dynacat 3.0, based on committed config, observed runtime state, and upstream primary sources.
**Constraint honored:** No deployment files were modified.

---

## 1. Executive verdict

**Do not switch. Pin the existing Glance deployment to v0.8.6 instead.**

- The running Glance image is **v0.8.5** (verified: the container's image index digest `sha256:32ab73d80f…` matches the Docker Hub index digest of the `v0.8.5` tag exactly; see §2.3). The live log shows repeated `Error fetching new reddit loid cookie, using cached value: no token found in challenge page` lines, meaning the Reddit **LOID-cookie refresh fails and Glance falls back to a cached cookie**. That does not by itself prove the displayed posts were stale; **user-visible freshness was never tested** (observed via Portainer by the parent agent; not independently re-fetched in this report).
- **Glance v0.8.6, released 2026-09-03, addresses exactly that warning.** Its changelog lists "Reddit widget not fetching new posts due to challenge page changes," plus an X-Forwarded-For auth rate-limit-bypass fix, unhealthy-container detection, and other concrete fixes ([v0.8.6 release notes](https://github.com/glanceapp/glance/releases/tag/v0.8.6)).
- Dynacat's own Reddit-403 issue [#141](https://github.com/Panonim/dynacat/issues/141) is **closed with the note "Fixed in glanceapp"**, linking upstream Glance commit `5879194`. The fix exists upstream; it did not originate in the fork.
- Dynacat 3.0.0, released **2026-09-12 18:36 UTC, hours before this report was written**, adds genuine unique features: **client-side dynamic widget updates** (SSE/polling), a **UI config editor**, a **read-only JSON data API**, **OIDC SSO**, and cross-page search results (§4). It also had essentially **zero soak time** at report time, and switching introduces fork-lifecycle risk (young independent repo, no visible test workflow) and deployment-model conflicts with the read-only git-sync config mount (§5-6).
- **Recommended action:** repoint `glanceapp/glance` to `v0.8.6` (or digest `sha256:9dfb09470b…` for the multi-arch index). A one-line compose change, low risk, and it resolves the observed cookie-refresh failure plus concrete security/fix items. Re-evaluate Dynacat after 3.0 has several weeks of soak, **if** live dynamic updates become a wanted feature.

---

## 2. Local baseline (as committed / as observed)

### 2.1 Compose (`services/glance/docker-compose.yml`, committed)

| Fact | Source line |
|---|---|
| Image `glanceapp/glance` **unpinned** (no tag, no digest) → tracks `latest` | L50 |
| `restart: unless-stopped` | L51 |
| Entrypoint `/app/glance --config /git/current/services/glance/config/glance.yml` | L52 |
| Config mounted **read-only**: `/opt/glance-configs:/git:ro` | L54 |
| Docker socket mount **commented out** (no docker-containers widget in use) | L55–56 |
| Ports `8080:8080` | L57–58 |
| Env passthrough: `GITHUB_TOKEN`, `AUTH_SECRET_KEY`, `ADMIN_PASSWORD`, `AWS_SSO_URL`, `INFRA_DOCS_URL`, `GRAFANA_URL`, `SPACELIFT_URL`, `CODEFRESH_URL`, `WIZ_URL` | L59–68 |
| `git-sync` pinned to `v4.4.2` digest, `--period=2s`, sparse-checkout of `services/glance/`, `--link=current` | L18–43 |

### 2.2 Config (`services/glance/config/`)

- `glance.yml`: `server.proxied: true`, `assets-path: /git/current/services/glance/assets`; password auth (single `admin` user via `${AUTH_SECRET_KEY}`/`${ADMIN_PASSWORD}`); Nord theme with `gruvbox-dark`/`zebra` presets; `custom-css-file: /assets/user.css`; **`$include: shared-library.yml`** and two included pages `home.yml`, `homelab.yml` (L3–42).
- Widgets actually in use: **11 distinct widget types**: `search` (perplexity engine, autofocus, new-tab, 6 bangs; `shared-library.yml` L12–30), `bookmarks` (multiple groups, `auto-invert` icons incl. URL icons), `releases` (2 instances, GitHub token, `cache: 5m`, `show-source-icon`), `rss` (`detailed-list`, `cache: 12h`, collapse-after), `lobsters`, `hacker-news`, `reddit` (5 subreddits, thumbnails), `clock` (3 timezones), `weather` (4 locations), `split-column`, `group`.
- Not used locally: monitor, playing/latest-media, docker-containers, speedtest, markets, to-do, videos, custom-api, dynawidgets. A **Plex** service does exist locally (`services/plex/docker-compose.yml`, `lscr.io/linuxserver/plex:latest`, host networking; live container observed on the TrueNAS Portainer environment); it simply has no dashboard widget yet.

### 2.3 Observed runtime state (reported by parent agent via Portainer; not independently re-fetched)

- `/glance` running image ID `sha256:00bf…`, **0 restarts** since 2026-08-29.
- Image digest `glanceapp/glance@sha256:32ab73d80f…`, created 2026-05-30.
- **Independent verification performed in this report:** the Docker Hub tag API's top-level index digest for `v0.8.5` is `sha256:32ab73d80f2b8b5fb0735b0431deb36b93fbb6b2fb43592449b0178c8b83e350`, an exact match. The running deployment is **Glance v0.8.5** (multi-arch index).
- Repeated log lines (Sep 3-12, observed via Portainer): `Error fetching new reddit loid cookie, using cached value: no token found in challenge page`. Exact observation: the Reddit **LOID-cookie refresh fails, then Glance uses a cached cookie**. Whether displayed posts were actually stale was **never tested**.

---

## 3. Fork lineage

- Dynacat's README states: **"Forked from Glance – it focuses on dynamic content updates and seamless integration with external applications."** ([README @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/README.md), retrieved 2026-09-12).
- GitHub metadata: `fork: false`, meaning **an independent copy, not a GitHub fork** ([api.github.com/repos/Panonim/dynacat](https://api.github.com/repos/Panonim/dynacat): created **2026-02-04**, `fork: false`, `archived: false`). Upstream lineage is self-declared in the README only; no fork-point commit is published. *(The absence of a published divergence commit is a gap: exact upstream-merge recency is not documented.)*
- Scale: Dynacat ~1.3k stars / 41 forks; Glance ~37k stars / 1.5k forks (repo views, retrieved 2026-09-12).
- Release cadence (Dynacat, from its releases API): 1.0.0 Feb 5 → 1.1.0 Feb 21 → 2.0.0 Mar 24 → 2.2.0 Apr 19 → 2.3.0 May 20 → 2.4.0 Jun 29 → **3.0.0 Sep 12, 2026** (75-day gap; [releases list](https://github.com/Panonim/dynacat/releases)). Glance: v0.8.6 2026-09-03, v0.8.5 2026-05-30, v0.8.4 2025-06-10 ([releases API](https://api.github.com/repos/glanceapp/glance/releases)).
- 3.0.0 was tagged at commit `d67959b` ("Merged beta branch into main"), verified-signed, published 2026-09-12 18:36 UTC ([3.0.0 release](https://github.com/Panonim/dynacat/releases/tag/3.0.0)).

---

## 4. Feature delta: Dynacat 3.0.0 vs. Glance v0.8.6

Baseline comparison is against **Glance v0.8.6** (the version the switch would effectively replace), because Glance already has auto-reload, `$include`, env interpolation, password auth, and all locally-used widgets.

### 4.1 Gains that are NOT gains (present in Glance v0.8.6 too; do not count toward switching)

| Feature | Glance evidence | Dynacat evidence |
|---|---|---|
| Config auto-reload (incl. included files) | [Glance docs, "Auto reload"](https://github.com/glanceapp/glance/blob/main/docs/configuration.md) | [Dynacat config docs @ 3.0.0, "Auto reload"](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md) |
| `$include` syntax, `${ENV}` interpolation, Docker secrets | Glance v0.8.0 release notes ("Nested config includes and new include syntax", "Using Docker secrets within the config") ([v0.8.0](https://github.com/glanceapp/glance/releases/tag/v0.8.0)) | Same constructs in Dynacat docs |
| Theme presets, custom CSS, HSL colors | Glance v0.8.0 ("Theme picker") | Dynacat docs "Theme" |
| Username/password auth | Glance v0.8.0 ("Authentication") | Dynacat [authentication docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/authentication.md) |
| All locally-used widgets (`bookmarks`, `releases`, `rss`, `lobsters`, `hacker-news`, `reddit`, `clock`, `weather`, `split-column`, `group`, `search` w/ bangs + perplexity) | Glance docs | Dynacat config docs (search widget table includes `perplexity`, `autofocus`, `new-tab`, `bangs`) |

### 4.2 Genuine Dynacat-unique deltas (documented in 3.0.0 sources)

| # | Feature | Local relevance | Source |
|---|---|---|---|
| D1 | **Dynamic client-side updates.** Page-level `dynamic-updates` toggle (default `true`); SSE updates, page-level polling, per-widget `update-interval` polling. Glance's FAQ states a page refresh is required to update feeds ([Glance README FAQ](https://github.com/glanceapp/glance)). | **High.** With client-side updates, the local `releases` widgets, 5× `reddit` and 4× `weather` widgets could refresh while the page is open instead of requiring a full page reload. Per-widget `update-interval` is independent of the widget's `cache:` setting (the releases widget's default `update-interval` is 3h, not the local `cache: 5m`). | [Dynacat config docs @ 3.0.0, page `dynamic-updates`](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md); [dynamic-updates docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/dynamic-updates.md); [3.0.0 release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0) |
| D2 | **UI config editor.** Drag/drop editing that writes back to the YAML; also a no-code custom-API **widget builder**. | **Conflicts with local architecture.** Config is synced via git-sync and mounted `:ro`; pages sourced from a read-only mount refuse editing and say so ([ui-editor docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/ui-editor.md)). The repo-as-source-of-truth workflow is the point of the current setup. | [3.0.0 release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0); [ui-editor docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/ui-editor.md); [server `allow-editing`/`editing-users` docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md) |
| D3 | **Read-only JSON API.** Per-widget `api-id`, secret stripping. Documented caveats: the API is **disabled by default**; when enabled without an `api.token`, anyone who can reach the endpoint can read widget data even if the dashboard requires login; an API request can refresh an expired cache, which is some additional upstream work. | **Low.** No current consumer (agent/automation) needs dashboard data. Interesting optionality, but the token-less-read default matters for a LAN-exposed dashboard. | [3.0.0 release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0); [api docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/api.md) |
| D4 | **Search results include bookmarks/Docker/monitors**, cross-page (`include-bookmarks`, `cross-page-bookmarks`, `include-docker`, `include-monitor`). | **Medium.** Local config has 20+ bookmark links across two pages; cross-page bookmark search is a real convenience. Docker/monitor parts are moot (widgets unused). | [Dynacat search widget property table @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md); [3.0.0 release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0) |
| D5 | **OIDC SSO** alongside password auth; brute-force protection (5 fails / 5 min, IP-based). | **Low-medium.** Only one local user; OIDC only useful if SSO integration is wanted. | [Dynacat authentication docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/authentication.md) |
| D6 | Extra widgets: `playing`/`latest-media` (Plex/Jellyfin/Emby/Navidrome), `torrenting`, `speedtest` (with previous-run comparison), `monitor` history/disabled, `dynawidgets` community templates, degoog search integration. | **Medium for `playing`/`latest-media`, low for the rest.** A Plex server exists per `services/plex/docker-compose.yml` (`lscr.io/linuxserver/plex:latest`, host networking, `/mnt/tank/media-lib`) with a live container on the TrueNAS Portainer environment. A "currently playing" / "recently added" row on the homelab page is therefore a **concrete follow-up opportunity**. It is not in the current dashboard and needs a Plex X-Plex-Token plus a network path from the dashboard host to Plex before it can be wired up. The other extras remain unneeded; Glance can approximate some via `custom-api`/community widgets ([glanceapp/community-widgets](https://github.com/glanceapp/community-widgets)). | [3.0.0 release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0); [currently-playing / latest-media docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md); local `services/plex/docker-compose.yml` |
| D7 | `server.trusted-proxies`. X-Forwarded-* is ignored unless the proxy is listed, even with `proxied: true`. | **A configuration requirement, not a feature gain.** Local `proxied: true` with no `trusted-proxies` means client IPs (and brute-force blocklists) would resolve to the proxy's IP after a switch. | [Dynacat `trusted-proxies` docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md); Glance v0.8.6 fixed "X-Forwarded-For spoofing which would allow rate-limit bypass for auth" ([v0.8.6 notes](https://github.com/glanceapp/glance/releases/tag/v0.8.6)) |

### 4.3 3.0.0 fix list vs. local needs

From the [3.0.0 release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0): Reddit 403 fix (see verdict), dynawidgets protocol/subrequest handling, calendar releases performance, currently-playing image reliability / Navidrome / Jellyfin, search highlighting, server-stats CPU temp, todo mobile UI, "several security issues", Go package updates.

- Locally relevant: **Reddit fix** (already upstream in Glance v0.8.6, see §1), **search highlighting** (minor UI), **security issues** (unspecified; no CVEs or issue links in the notes, so *evidence absent*).
- Locally present but unexercised: the **currently-playing / Plex fixes** matter only once the `playing`/`latest-media` widgets are actually configured. Those widgets are absent from the current dashboard, so the 3.0.0 fixes buy nothing today; the built-in Plex widgets remain a medium-value opportunity on their own because Plex exists locally (D6).
- Not locally relevant: calendar, Jellyfin, Navidrome, todo, dynawidgets (none of these widgets are deployed).

---

## 5. Stability evidence

**Dynacat 3.0.0**
- **Age:** released 2026-09-12 18:36 UTC, **hours old at report time (same day)** ([release](https://github.com/Panonim/dynacat/releases/tag/3.0.0)). *Inference: soak-time risk; no long-term behavior data exists yet.*
- **Release cadence:** frequent through v2.4.0 (13 releases Feb-Jun 2026: 1.0.0, 1.0.1, 1.1.0, 2.0.0, 2.0.1, 2.1.0, 2.2.0, 2.2.1, 2.2.2, 2.2.3, 2.3.0, 2.3.1, 2.4.0), then a 75-day gap to 3.0.0. The 3.0 line is a beta-branch merge ("Merged beta branch into main", commit `d67959b`).
- **Immediate post-release issues:** [#148](https://github.com/Panonim/dynacat/issues/148) (Unix-socket proxy support; a feature request, opened 2026-09-12 21:00 UTC, hours after the release) and [#146](https://github.com/Panonim/dynacat/issues/146) (Jellyfin 12.0 query-auth → 401 on v2.4.0; opened 2026-09-09, **closed 2026-09-12 before the 3.0.0 release**). Open-issue count is 3 ([repo API](https://api.github.com/repos/Panonim/dynacat)). *(No stability conclusion can be drawn from three issues on a 7-month-old repo; listed as facts.)*
- **CI:** workflows are Deploy/Docs/Dependabot/Dependency Graph/pages. **No visible test workflow** (`.github/workflows/deploy.yml` builds multiarch image + binaries; [workflow list](https://api.github.com/repos/Panonim/dynacat/actions/workflows)). *No visible workflow runs tests, so public CI provides no test-execution evidence; it does not establish whether tests exist or run elsewhere.*
- **Performance claim:** maintainer's own benchmark, **2.4.0 vs. 3.0.0 only** (not vs. Glance): CPU 0.05%→0.02%, RAM 22.13→12.34 MiB, network 5.03/5.95 MB→389/97.1 kB ([3.0.0 notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0)). No methodology stated; not independently reproducible from the release notes; not a comparison against Glance. Treated as marketing, not evidence.
- **Docker image:** built from `golang:1.26-alpine`, runtime `alpine:3.21` + zfs; entrypoint `/app/dynacat --config /app/config/dynacat.yml` ([Dockerfile @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/Dockerfile)).

**Glance v0.8.5/v0.8.6**
- **Active defect in the running v0.8.5:** repeated `Error fetching new reddit loid cookie, using cached value: no token found in challenge page` log lines Sep 3-12 (parent-observed via Portainer). The Reddit LOID-cookie refresh fails and the cached cookie is used; whether displayed posts were stale was never tested. Observed restart count: 0 since 2026-08-29 (a restart count alone is not a health statement).
- **v0.8.6 (2026-09-03)** fixes the Reddit cookie breakage (changelog: "Reddit widget not fetching new posts due to challenge page changes") plus: X-Forwarded-For auth rate-limit bypass, unhealthy-docker-container detection, stale selfh.st icons, engagement sorting, search-bang indicator, DNS-stats without password, webp icons, relative-path RSS thumbnails, `base-url` manifest path ([v0.8.6 notes](https://github.com/glanceapp/glance/releases/tag/v0.8.6)).
- **Open Glance issues around v0.8.6** (Sept 6-11, per parent agent; not individually re-verified): #1077 `mountpoint:info` duplicate branch, #1076 case-sensitivity, and #1075, a PR "Fall back to the feed URL when a feed's own link is relative" (relative-item-link RSS feeds, `ZgotmplZ` hrefs). **#1075's RSS link path is locally relevant** (the local RSS widget uses 6 feeds); it is a rendering edge case for feeds whose item links are relative, and a confirmed breakage of the local feeds has not been observed. *Inference: Glance's larger codebase has a larger bug surface; one open RSS-link item touches a locally-used widget, but is an edge case rather than a core-path break.*
- **CI:** Glance has Create-release + CodeQL workflows ([workflow list](https://api.github.com/repos/glanceapp/glance/actions/workflows)).
- **Security track record:** both projects have shipped auth-related fixes. Glance v0.8.6's XFF-spoofing fix is concrete and cited; Dynacat's 3.0 "several security issues" are uncited. *(Evidence-quality asymmetry in favor of Glance.)*

**Head-to-head:** there is no documented direct stability comparison between the two projects, and Dynacat's only benchmark is intra-project. The only observed, local stability fact is the running Glance v0.8.5's repeated Reddit cookie-refresh failure, which Glance v0.8.6 addresses.

---

## 6. Migration risks (switching to Dynacat 3.0)

| Risk | Severity | Detail / source |
|---|---|---|
| **R1. Zero-soak release** | High | 3.0.0 shipped 2026-09-12; beta-branch merge; 75-day dev gap before it ([release](https://github.com/Panonim/dynacat/releases/tag/3.0.0)). |
| **R2. Young independent fork** | High | Repo created 2026-02-04, `fork: false` (an independent copy; [repo API](https://api.github.com/repos/Panonim/dynacat)). The exact upstream divergence point and sync status are **not established** (lineage is self-declared in the README only; no published fork-point commit). Single primary maintainer visible on the release (contributors: 3, mostly beta feedback). *Inference: bus-factor/sync-drift risk.* |
| **R3. UI editor vs. read-only git-sync mount** | Medium | Config lives in a git-synced dir mounted `:ro` (compose L54); the 3.0 editor writes YAML back ([release notes](https://github.com/Panonim/dynacat/releases/tag/3.0.0)) and pages sourced from a read-only mount [refuse editing](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/ui-editor.md), so the feature is unusable here. A pilot should set `ENABLE_EDITOR=false` (env var: hides the button, unloads editor assets, unregisters `/api/editor/*`; with it set, `server.allow-editing`/`editing-users`/`editing-groups` are ignored with a startup warning), or use `server.allow-editing: false` as the config-only alternative ([docker-options docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/docker-options.md)). |
| **R4. Reload/cache interaction with git-sync `--period=2s`** | Medium | Both projects clear widget caches on config reload (documented CAUTION in Dynacat docs; Glance docs identical). git-sync replaces files when upstream HEAD changes, so any upstream push to the config repo triggers a reload and a full cache refetch. The behavior is the same on Glance, so this is a shared risk; D1 (live updates) makes frequent mid-session reloads more visible. *Inference; verify reload behavior during the pilot.* |
| **R5. `trusted-proxies` required for correct IPs** | Low | Without it, `X-Forwarded-*` is ignored even with `proxied: true` (Dynacat docs §`trusted-proxies`); brute-force protection would key off the proxy IP. One config line to fix. |
| **R6. Missing env vars are hard errors** | Low | Dynacat: "Attempting to use an environment variable that doesn't exist will result in an error and Dynacat will either not start or load your new config on save" (docs). All 9 local env vars are passed through; risk only if compose env is edited later. |
| **R7. Image/config-path + entrypoint changes** | Low | New image `panonim/dynacat`, default config path `/app/config/dynacat.yml`. The local compose's entrypoint `/app/glance --config …` (compose L52) **must be replaced with `/app/dynacat --config …`** (Dockerfile @ 3.0.0 entrypoint). Passing `--config` to the existing path alone leaves the image invoking an absent `/app/glance` executable. The original "file needs renaming" startup error ([issue #110](https://github.com/Panonim/dynacat/issues/110)) was **fixed upstream** (closed 2026-06-01 as completed); a `glance.yml` name is no longer a blocker, only the entrypoint and `--config` path need to match. |
| **R8. Unpinned image on both sides** | Low | Current compose is unpinned (`glanceapp/glance`). The 3.0.0 **multi-arch index digest is published on Docker Hub: `sha256:974563ad02c190f6a3e1240a096b8927136145956f2c202c17ffbb47d5a9c367`** ([tag API](https://hub.docker.com/v2/repositories/panonim/dynacat/tags/3.0.0), verified 2026-09-12; amd64 22,813,365 B / arm64 22,104,351 B), so pinning `panonim/dynacat:3.0.0@sha256:9745…` is possible. |

**Net:** no documented *compatibility* blocker (the local config (includes, anchors, env, theme, all 11 widget types) is documented as supported by Dynacat), but the risk profile is dominated by R1/R2, which no amount of config testing can retire quickly.

---

## 7. Recommendations

1. **Now (low effort, high value): pin and update Glance to v0.8.6.**
   Change `services/glance/docker-compose.yml` L50 from `image: glanceapp/glance` to `image: glanceapp/glance:v0.8.6` (or `glanceapp/glance@sha256:9dfb09470b207dcb67ac715994bdb1929374ba3f9c0d7df7462c24adf10fd073`, the v0.8.6 multi-arch index digest, verified against the Docker Hub API). This addresses the live cookie-refresh failure (the v0.8.6 changelog item "Reddit widget not fetching new posts due to challenge page changes" matches the observed log error), pulls in the XFF-spoofing security fix, and removes the unpinned-`latest` exposure. Verify post-deploy: the `loid cookie` error stops.
2. **Do not switch to Dynacat yet.** The only locally compelling Dynacat deltas are D1 (live dynamic updates) and D6's Plex `playing`/`latest-media` (Plex exists locally, but the widget is not configured and needs a token + network path). D2 is architecturally incompatible with the git-sync setup; D3/D4/D5 are nice-to-haves. A same-day major release from a 7-month-old independent fork does not outweigh a one-line Glance pin.
3. **If D1 (dynamic updates) becomes a must-have:** pilot Dynacat 3.0 **beside** Glance (separate compose file, port 8081) for ≥2–4 weeks:
   - pin `panonim/dynacat:3.0.0@sha256:974563ad02c190f6a3e1240a096b8927136145956f2c202c17ffbb47d5a9c367` (Docker Hub multi-arch index digest, verified 2026-09-12);
   - reuse the existing git-sync mount `:ro` and **disable the editor: set `ENABLE_EDITOR=false`** (env var: hides the button, unloads editor assets, unregisters `/api/editor/*`; with it set, `server.allow-editing`/`editing-users`/`editing-groups` are simply ignored with a startup warning). If the env var is unavailable, `server.allow-editing: false` is the config-only alternative ([docker-options docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/docker-options.md); [ui-editor docs @ 3.0.0](https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/ui-editor.md));
   - add `server.trusted-proxies` with the Cloudflare tunnel/proxy IP (R5);
   - replace the compose entrypoint `/app/glance` with `/app/dynacat` (per R7), keep the existing `glance.yml` contents as the config entry point (format-compatible per §4.1; pass `--config` to it; per R7 the file name itself is not a blocker), and smoke-test all 11 widget types plus the two `releases` widgets with the GitHub token;
   - cutover only after the pilot shows no regressions in RSS/reddit/releases polling under the 2s git-sync cadence.
4. **Watch list:** Dynacat's next patch after 3.0.0 (soak evidence, whether #146-class regressions recur), and Glance's `main` post-v0.8.6 commits (3 commits already exist post-release per the v0.8.6 page). If Glance ships client-side dynamic updates upstream, the primary reason to fork evaporates.

---

## 8. Primary sources

**Dynacat (docs cited at the 3.0.0 tag `d67959b`. The tag is not marked immutable on the release API, so raw links at the tagged commit are preferred)**
- Repo / README ("Forked from Glance", features, common issues) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/README.md (repo root: https://github.com/Panonim/dynacat)
- 3.0.0 release notes (features, fixes, benchmark table, contributors): https://github.com/Panonim/dynacat/releases/tag/3.0.0
- Releases list (cadence): https://github.com/Panonim/dynacat/releases
- Issue #141 Reddit 403 ("Fixed in glaceapp", links Glance commit 5879194, closed 2026-09-12): https://github.com/Panonim/dynacat/issues/141
- Config docs (auto-reload, env, `$include`, server props incl. `trusted-proxies` + `allow-editing`, search widget, page `dynamic-updates`, currently-playing/latest-media, icons, theming) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/configuration.md
- Auth docs (password + OIDC, brute-force protection, editing access control) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/authentication.md
- Dynamic-updates docs (SSE/polling, `update-interval`) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/dynamic-updates.md
- API docs (disabled by default, token-less-read warning, rate-limit) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/api.md
- UI editor docs (read-only-mount behavior, pencil-icon controls) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/ui-editor.md
- Docker options (`ENABLE_EDITOR`, `ENABLE_DYNAMIC_UPDATE`, etc.) @ 3.0.0: https://github.com/Panonim/dynacat/blob/3.0.0/docs/docs/docker-options.md
- CI workflows: https://api.github.com/repos/Panonim/dynacat/actions/workflows (deploy.yml: https://raw.githubusercontent.com/Panonim/dynacat/main/.github/workflows/deploy.yml)

**Glance**
- Repo / README (FAQ: page refresh required for updates; custom widgets incl. community): https://github.com/glanceapp/glance
- v0.8.6 release (2026-09-03): https://github.com/glanceapp/glance/releases/tag/v0.8.6
- v0.8.0 release (auth, theme picker, `$include`, secrets, includes-nesting): https://github.com/glanceapp/glance/releases/tag/v0.8.0
- Releases (cadence): https://api.github.com/repos/glanceapp/glance/releases
- Config docs (auto-reload, `proxied`, search widget w/ perplexity + bangs): https://github.com/glanceapp/glance/blob/main/docs/configuration.md
- Community widgets: https://github.com/glanceapp/community-widgets
- CI workflows: https://api.github.com/repos/glanceapp/glance/actions/workflows

**Local files (unmodified)**

- `services/glance/docker-compose.yml`, `services/glance/config/glance.yml`, `home.yml`, `homelab.yml`, `shared-library.yml` (line numbers cited in §2); `services/plex/docker-compose.yml` (Plex service evidence for D6)
- Docker Hub tag/digest mapping (verified 2026-09-12): https://hub.docker.com/v2/repositories/glanceapp/glance/tags (v0.8.5 index = `sha256:32ab73d80f…` matches running image; v0.8.6 index = `sha256:9dfb09470b…`) and https://hub.docker.com/v2/repositories/panonim/dynacat/tags/3.0.0 (3.0.0 multi-arch index = `sha256:974563ad02c190f6a3e1240a096b8927136145956f2c202c17ffbb47d5a9c367`, amd64 22,813,365 B / arm64 22,104,351 B)

**Provenance note:** Portainer observations (running digest, 0 restarts, Reddit log errors) were reported by the main agent during this session and were *not* independently re-fetched; the digest→tag mapping was independently re-verified against the Docker Hub API. All "inference" items are explicitly marked in the body.
