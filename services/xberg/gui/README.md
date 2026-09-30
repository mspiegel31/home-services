# xberg GUI (tier B)

A single-file vanilla JS web UI in front of the xberg API, plus an nginx
sidecar that serves it and reverse-proxies `/api/*` to xberg. No build step,
no node toolchain, no framework.

## Files

- `index.html` — the whole app (markup + CSS + JS in one file).
- `nginx.conf` — serves the page at `/`, proxies `/api/*` → `xberg:8000/`.

Both are delivered to the containers by the **git-sync sidecar** in
`docker-compose.yml` (same `xberg-config` named volume as `xberg.toml`), so
editing them in git is enough — no tank copy, no rebuild.

## What it does

- **Convert tab**: drop PDF/JPG/JPEG/PNG scans (multi-file) → a bounded
  parallel worker pool of sync `POST /extract` jobs → **one status card per
  file** with live state (`QUEUED` → `RUNNING` → `OK` / `TEXT` / `EMPTY` /
  `ERROR`) and per-job timing. `OK`/`TEXT` cards show the structured recipe
  (title, meta, ingredients, steps, tags), the raw output, and **Copy JSON** /
  **Copy Mealie JSON** buttons. A summary line tracks `done/total · running ·
  queued · ok · error`.
- **Server tab**: live `/health`, `/info`, `/formats`, `/cache/stats`.
- Header health dot polls `/health` every 30s.

The `config` override sent per request is exactly what
`scripts/ingest_recipes.py` sends: `{ "force_ocr": true, "output_format": ... }`.
The **recipe schema and LLM routing are inherited from `xberg.toml`** — this
page does not send a schema. Structured output only appears when
`structured_extraction` is enabled server-side (it is, in the current
`xberg.toml`).

## Options

- **Force OCR** (default on) — `force_ocr: true`.
- **VLM fallback** (default off) — per-request override `ocr.vlm_fallback.mode`.
  Gated because the request-level override path is less exercised than the
  server default. For a reliably-VLM cookbook pass, set
  `vlm_fallback.mode = "always"` in `xberg.toml` (the durable fix) rather than
  relying on the per-request toggle.
- **Output** — `markdown` (default) / `plain` / `djot` / `html` / `json` /
  `doctags`.
- **Concurrency** (default 2) — how many jobs run in parallel. `1` is fully
  sequential (the safe default if you're seeing server-side pressure); raise it
  for throughput. The pool bounds concurrency, so the status-per-job view is
  the point: you can see which pages are queued vs. running vs. done.

## Access

nginx binds `0.0.0.0:8998` on the host (LAN-exposed). From the LAN:
`http://<host-ip>:8998`. The xberg API behind it stays loopback-only
(`127.0.0.1:8999`) — only the GUI port is open to the LAN, and nginx
forwards `/api/*` to xberg on the internal `xberg` network.

## Why sync `/extract` per job, not `/extract-async`

`/extract-async` jobs **expire after 5 minutes**. A VLM pass on a dense
handwritten page can take close to the 300s model timeout, and a queued job
that's still pending past the window returns 404. The bridge script
(`scripts/ingest_recipes.py`) sidesteps this with one sync `/extract` per
file. The GUI does the same — but runs them through a bounded worker pool
instead of strictly one-at-a-time, so you get per-job status without the
expiry trap. Concurrency `1` reproduces the exact sequential behavior.

## Portainer notes

- No `env_file` — nothing here needs one.
- `nginx:1.27-alpine` ships `wget` (busybox), used by the healthcheck.
- The GUI and xberg share the `xberg` network; nginx reaches xberg by
  service name `xberg:8000`.
