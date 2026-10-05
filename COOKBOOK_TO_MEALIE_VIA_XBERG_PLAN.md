# Cookbook → Mealie via Xberg

## Context

Digitize old cookbooks into the existing Mealie stack. Cookbook pages become PDFs/JPEGs (phone/flatbed) dropped into a folder on the ZFS tank; we run them through **Xberg** (one container, the "throw anything at this" home document engine) using the **existing `swift-1.5-bf16` vLLM lane** as the vision-OCR + recipe-structuring engine (no new model deployment), then push the resulting structured recipes into Mealie via its API. End state: drop a scan into the folder, run one script, the recipe appears in Mealie with correct name/ingredients/steps; re-running is idempotent (no duplicates).

Decision already made with the user: **Xberg** (not paperless-ngx, not docling). Rationale: broadest format coverage, native VLM-OCR backend that points at vLLM, built-in schema-driven JSON extraction (collapses parse→structure→Mealie into one pass), MCP/REST, CPU-default and lean. Docling wins on classical table/OCR quality and maturity but is slow, RAM-heavy, PDF-centric, and has no built-in schema extraction; its main edge is bypassed because both are fed the same swift-1.5-bf16 VLM for the hard pages.

## Architecture (fixed)

```
scan PDF/JPEG ──> /mnt/tank/container-configs/xberg/scan-inbox/   (ZFS, phone/flatbed drops here)
                          │  (bridge script reads folder)
                          ▼
                 POST http://xberg:8000/extract   (multipart: files + config)
                          │  xberg: classical OCR (tesseract) first,
                          │         vlm_fallback=on_low_quality → swift-1.5-bf16 for bad pages
                          │         structured_extraction → swift-1.5-bf16 → recipe JSON
                          ▼
                 recipe JSON (title/ingredients/steps/...)
                          │  (bridge script)
                          ▼
                 POST http://<mealie>:9000/api/recipes   (Bearer: long-lived API token)
                          │  dedup by name first (GET /api/recipes?queryFilter=...)
                          ▼
                      Mealie
```

New files (all under `services/xberg/`):
- `services/xberg/docker-compose.yml`
- `services/xberg/xberg.toml`
- `services/xberg/recipe_schema.json`
- `services/xberg/scripts/ingest_recipes.py`
- `services/xberg/.env.example`

## Approach

### Step 1 — Xberg container + config

Create `services/xberg/docker-compose.yml`. One service, `xberg`, following the repo's Portainer conventions (no `env_file`; declare `${VAR}` explicitly; host-config mounts under `/mnt/tank/container-configs/xberg/`; `deploy.resources.limits`).

Service spec (exact):
- `image: ghcr.io/xberg-io/xberg:latest`  ← **unverified — confirm this repo:tag exists and pulls on the first `docker compose pull`; if the tag differs (e.g. a dated `v1.x.y`), pin that and proceed.**
- `restart: unless-stopped`, `init: true`, `security_opt: [no-new-privileges:true]`
- `command: ["xberg", "serve", "-H", "0.0.0.0", "-p", "8000", "--config", "/config/xberg.toml"]`
- `environment:`
  - `XBERG_CACHE_DIR: /data/cache`
  - `XBERG_OCR_LANGUAGE: eng`
  - `TZ: "${TZ:?Set TZ in Portainer}"`
  - (No `XBERG_LLM_*` env vars — all LLM routing lives in `xberg.toml` so it is version-stable and git-synced.)
- `volumes:`
  - `./xberg.toml:/config/xberg.toml:ro`
  - `/mnt/tank/container-configs/xberg/cache:/data/cache`
  - `/mnt/tank/container-configs/xberg/scan-inbox:/inbox:ro`
- `ports: ["127.0.0.1:8999:8000"]` (bind to loopback; the bridge reaches it by service name on the internal network, so no LAN exposure)
- `healthcheck: { test: ["CMD", "wget", "-qO-", "http://127.0.0.1:8000/health"], interval: 30s, timeout: 5s, retries: 10, start_period: 30s }`
- `deploy.resources.limits: { memory: 4G, cpus: "4.0" }` (classical OCR + layout/table models are CPU; VLM work is offloaded to the GPU lane)
- `networks: [xberg]`

Create `services/xberg/xberg.toml`. Exact content:

```toml
# Xberg config for cookbook → Mealie.
# VLM OCR + structured extraction both use the existing swift-1.5-bf16 vLLM lane.
# The vLLM OpenAI-compatible base is reached via the llama-swap router.

[ocr]
language = ["eng"]
# Classical backend runs first; only pages scoring below the threshold go to the VLM.
backend = "tesseract"
vlm_fallback = "on_low_quality"
quality_threshold = 0.5

[ocr.vlm_config]
model = "swiftvl/swift-1.5-bf16"
base_url = "http://192.168.1.98:11437/v1"
api_key = "none"
timeout_secs = 300

[[ocr.vlm_config.providers]]
name = "swiftvl"
base_url = "http://192.168.1.98:11437/v1"
auth_header = "Authorization"
model_prefixes = ["swiftvl/"]

[structured_extraction]
schema_name = "recipe"
schema_description = "A single cookbook recipe. Return one recipe per document."
strict = true

[structured_extraction.llm]
model = "swiftvl/swift-1.5-bf16"
base_url = "http://192.168.1.98:11437/v1"
api_key = "none"
timeout_secs = 300

[[structured_extraction.llm.providers]]
name = "swiftvl"
base_url = "http://192.168.1.98:11437/v1"
auth_header = "Authorization"
model_prefixes = ["swiftvl/"]
```

Config notes (do not re-decide):
- `vlm_fallback = "on_low_quality"` synthesizes a `[tesseract, vlm]` pipeline; `quality_threshold = 0.5` is the accept bar (0.7/0.3 blend of text-shape quality and confidence). To force the VLM on every page (max quality, more GPU) change it to `vlm_fallback = "always"` — that is a tuning knob, not a structural choice.
- `base_url` `http://192.168.1.98:11437/v1` is the pinned llama-swap→vLLM endpoint already used by `services/litellm/models/swift-1.5-bf16.yaml` (`api_base: http://192.168.1.98:11437/v1`, `custom_llm_provider: hosted_vllm`). **unverified — confirm xberg's liter-llm actually routes `swiftvl/swift-1.5-bf16` to that base_url in Step 2's `xberg doctor`; if the custom-provider block is rejected, fall back to `model = "vllm/swift-1.5-bf16"` and set `base_url` directly on `vlm_config`/`llm` (drop the `[[...providers]]` tables).**
- `structured_extraction.schema` is **not** in the TOML; the bridge supplies it per-request via the `/extract` `config` field (see Step 3), loading `recipe_schema.json`. This keeps the schema versioned with the bridge, not the container.

Create `services/xberg/.env.example` documenting the one Portainer secret the bridge needs (set in Portainer UI, never committed):
```
# Set in Portainer UI for the xberg stack; the bridge script reads it at runtime.
XBERG_MEALIE_TOKEN=<long-lived Mealie API token>
```

### Step 2 — Verify xberg + VLM reachability (gate for the rest)

Prereq: the `swift-1.5-bf16` lane is up on the GPU host and `192.168.1.98:11437/v1/models` returns a model list (the llama-swap router). This is already how OMP reaches it, so no new infra.

Commands (run where the xberg container is reachable):
1. `docker compose -f services/xberg/docker-compose.yml up -d`
2. `curl -fsS http://127.0.0.1:8999/health` → expect `{"status":"healthy",...}`.
3. `docker compose -f services/xberg/docker-compose.yml exec xberg xberg doctor --config /config/xberg.toml` → expect the VLM/LLM backend to report reachable (no validation error about `vlm_config`). This is the check that the `swiftvl` provider routing works.
4. One-page smoke: take a single clean cookbook page `sample.pdf`, `curl -F "files=@sample.pdf" -F 'config={"force_ocr":true}' http://127.0.0.1:8999/extract` → expect `results[0].content` non-empty readable text.

If Step 2.3/2.4 show the VLM path is not routing: apply the fallback in Step 1's config note (`vllm/` prefix + direct `base_url`) and re-run 2.3/2.4 before continuing.

### Step 3 — Recipe schema

Create `services/xberg/recipe_schema.json`. This is the JSON Schema xberg's `structured_extraction` enforces (strict mode) and the bridge maps onto Mealie's `Recipe` model. Exact content:

```json
{
  "type": "object",
  "properties": {
    "title":      { "type": "string", "description": "Recipe name, clean title case." },
    "description":{ "type": ["string", "null"], "description": "Short intro/notes if present." },
    "servings":   { "type": ["string", "null"], "description": "Yield, e.g. \"4 servings\"." },
    "prep_time":  { "type": ["string", "null"] },
    "cook_time":  { "type": ["string", "null"] },
    "ingredients":{
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "quantity": { "type": ["number", "null"] },
          "unit":     { "type": ["string", "null"] },
          "name":     { "type": "string" },
          "note":     { "type": ["string", "null"] }
        },
        "required": ["name"]
      }
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "text": { "type": "string" }
        },
        "required": ["text"]
      }
    },
    "tags":       { "type": "array", "items": { "type": "string" } },
    "categories": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["title", "ingredients", "steps"]
}
```

Scope boundary (one line): one recipe per input file. The script processes a folder of files; if a single file holds multiple recipes, the user splits it into one-page/one-recipe files first — the schema is single-recipe by design.

### Step 4 — Bridge script `ingest_recipes.py`

Create `services/xberg/scripts/ingest_recipes.py`. Python 3 stdlib only (`urllib.request`, `json`, `os`, `argparse`, `sys`, `pathlib`) — no pip deps, runs on the host (or in a one-off container) where it can reach both xberg and Mealie. Behavior:

Config (env vars, read at runtime):
- `XBERG_URL` (default `http://127.0.0.1:8999`)
- `MEALIE_URL` (default `http://192.168.1.39:9000`)
- `XBERG_MEALIE_TOKEN` (required; the Mealie long-lived API token)
- `SCAN_DIR` (default `/mnt/tank/container-configs/xberg/scan-inbox`)

CLI: `python3 ingest_recipes.py [--dir SCAN_DIR] [--dry-run]`

Per-file algorithm (files matching `*.pdf *.PDF *.jpg *.jpeg *.png`, sorted):
1. Build the per-request config: load `recipe_schema.json` (resolved relative to the script's parent dir), then
   `cfg = {"force_ocr": True, "output_format": "markdown", "structured_extraction": {"schema": <schema>, "schema_name": "recipe", "strict": True}}`.
2. `POST {XBERG_URL}/extract` as multipart form: field `files` = the scan bytes; field `config` = `json.dumps(cfg)`. Read JSON.
3. Pull `results[0].structured_output` (the recipe object). If missing/empty, or `results[0]` is in the `errors` array → log `SKIP <file>: no structured output` and continue (do not abort the batch).
4. **Dedup:** `GET {MEALIE_URL}/api/recipes?queryFilter=name = "<title>"&perPage=1` with `Authorization: Bearer <token>`. If `total > 0` → log `EXISTS <title>` and continue.
5. Map the recipe object to Mealie's `Recipe` body (exact field mapping, use `camelCase` keys as Mealie expects):
   - `name` ← `title`
   - `description` ← `description` (or `""`)
   - `recipeYield` ← `servings` (or `""`)
   - `prepTime` / `cookTime` ← `prep_time` / `cook_time` (or `null`)
   - `recipe_ingredient` ← for each ingredient: `{"quantity": q, "unit": {"name": unit} if unit else None, "food": {"name": name}, "note": note or "", "disable_amount": false}`. If `quantity` is null, set `quantity: 1` and `disable_amount: true` (Mealie treats it as a note-only line).
   - `recipe_instructions` ← for each step: `{"text": step.text}` (omit `title`/`summary`/`ingredient_references`).
   - `tags` ← `tags` (list of strings; Mealie auto-creates missing tags)
   - `recipe_category` ← `categories` (list of strings)
   - `extras` ← `{"source_file": "<filename>"}` (traceability; Mealie extras are API-only key/value pairs)
6. `POST {MEALIE_URL}/api/recipes` with `Authorization: Bearer <token>` and the JSON body. Expect `201` and a slug string. Log `CREATED <title> -> <slug>`.
7. `--dry-run` stops after step 3 and prints the would-be Mealie body; no dedup, no POST.

Error handling: wrap each file in try/except; a per-file failure logs `FAIL <file>: <exc>` and continues. Exit code 0 if all files processed (skips/exists/fails included), 1 only if the xberg or mealie base URL is unreachable at start (fail fast, before the loop).

Why this shape: Mealie's `POST /api/recipes` (`create_one_api_recipes_post`) accepts the full `Recipe` document and returns the slug; `Recipe`'s validators auto-slug `name`, auto-create string `tags`/`recipe_category`, and build `display` for each ingredient from `quantity`/`unit`/`food`/`note`. `RecipeIngredient` fields are `quantity`(float), `unit`(object w/ `name`), `food`(object w/ `name`), `note`(str); `RecipeStep` requires `text`. This is the minimal correct body — no `id`/`user_id`/`group_id` (server-assigned).

### Step 5 — Run a real batch

1. Confirm `swift-1.5-bf16` lane is loaded on the GPU host.
2. Ensure at least 3 real cookbook scans are in `SCAN_DIR`.
3. `XBERG_MEALIE_TOKEN=<token> MEALIE_URL=http://192.168.1.39:9000 python3 services/xberg/scripts/ingest_recipes.py --dir /mnt/tank/container-configs/xberg/scan-inbox`
4. Watch logs: expect `CREATED <title> -> <slug>` per new recipe, `EXISTS` on re-run.

## Critical files & anchors

- `services/xberg/xberg.toml` — the VLM/LLM routing + `vlm_fallback` policy. The whole "use swift-1.5-bf16, no new model" decision lives here.
- `services/xberg/scripts/ingest_recipes.py` — the only new logic; the xberg→Mealie mapping (Step 4.5) is the load-bearing transform.
- `services/mealie/docker-compose.yml` (existing, read-only reference) — Mealie is on `192.168.1.39:9000`, `ALLOW_SIGNUP=false` (use the API token, not signup).
- `services/litellm/models/swift-1.5-bf16.yaml` (existing, read-only reference) — source of the pinned vLLM base `http://192.168.1.98:11437/v1` and model id `swift-1.5-bf16`.
- `services/xberg/recipe_schema.json` — the contract between xberg structured output and the bridge's Mealie mapping.

## Verification

1. **Container healthy:** `curl -fsS http://127.0.0.1:8999/health` → `{"status":"healthy",...}`.
2. **VLM routes to swift (the key new behavior):** `docker compose -f services/xberg/docker-compose.yml exec xberg xberg doctor --config /config/xberg.toml` reports the VLM backend reachable with no `vlm_config` validation error; and a one-page `curl -F "files=@sample.pdf" -F 'config={"force_ocr":true}' http://127.0.0.1:8999/extract` returns readable `content` (proves page images actually reach the 27B VLM, not just tesseract).
3. **End-to-end new recipe:** run the bridge on a folder with 1 fresh cookbook scan that is not yet in Mealie → expect log `CREATED <title> -> <slug>` AND `curl -H "Authorization: Bearer <token>" http://192.168.1.39:9000/api/recipes/<slug>` returns the recipe with non-empty `recipe_ingredient` and `recipe_instructions` matching the page.
4. **Idempotency:** re-run the bridge on the same folder → expect `EXISTS <title>` and no new recipe (Mealie recipe count unchanged).
5. **Graceful skip:** drop a non-recipe image (e.g. a photo) into a scratch dir, run with `--dir` on it → expect `SKIP <file>: no structured output` (or `FAIL`), exit 0, no crash.

## Assumptions & contingencies

- **Scan source:** phone/flatbed produces PDFs/JPEGs into `/mnt/tank/container-configs/xberg/scan-inbox/` (chosen by user). The folder is the only input; the script never watches/polls it.
- **One recipe per file.** If a user's scan has multiple recipes per page/file, split into one-recipe-per-file before running (schema is single-recipe). No auto-splitting logic is built.
- **`ghcr.io/xberg-io/xberg:latest`** is assumed pullable. If the registry path/tag differs, pin the real one (Step 2.1) — everything else is unaffected.
- **vLLM base routing** via xberg's custom `swiftvl` provider is assumed to work. Fallback if `xberg doctor` rejects it: use `model = "vllm/swift-1.5-bf16"` with `base_url` set directly on `vlm_config`/`llm` and delete the `[[...providers]]` tables (Step 1 note / Step 2).
- **Mealie token:** a long-lived API token must be created at Mealie's `/user/profile/api-tokens` and supplied as `XBERG_MEALIE_TOKEN`. Not created by this plan.
- **GPU contention:** VLM OCR competes for the swift-1.5-bf16 lane with normal chat traffic. `on_low_quality` (default) minimizes this by sending only weak pages to the VLM. If the user wants max fidelity and accepts the contention, set `vlm_fallback = "always"` in `xberg.toml`.
- **No archive/search layer** is added (xberg is a converter, not a vault). Scans remain plain files on the tank; Mealie is the system of record for recipes. This is intentional per the lean-stack choice.
