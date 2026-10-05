# Grafana observability for litellm + llama-swap (metrics, traces, logs)

## Context

Today the inference stack (LiteLLM :4000 → llama-swap :11437 → ephemeral vLLM backends, all on inference box 192.168.1.98) has no persistent telemetry; tok/s per model is visible only ad-hoc. Goal: a small Grafana instance on the **TrueNAS box (192.168.1.39)** storing metrics + traces + logs, fed by the inference box, using this repo's docker-compose + git-sync + Portainer-CE stack conventions. Inference box runs one collector container (Grafana Alloy) that scrapes/receives locally (vLLM backends are only reachable on the `llama-swap-vllm-backend` docker network) and ships everything over LAN to TrueNAS.

End state: Grafana at `http://192.168.1.39:3000` with a provisioned "Inference" dashboard showing per-model tok/s (gateway and engine), TTFT/ITL, KV-cache and GPU stats; Explore wired to Loki (litellm/llama-swap/vLLM container logs, incl. model load failures) and Tempo (per-request LiteLLM traces).

Signal routing (fixed):
- **Metrics**: Alloy (inference box) scrapes `litellm /metrics` (bearer master key), `llama-swap /metrics` (GPU/system), vLLM backends `http://<container>:8000/metrics` via docker discovery on the existing `io.mspiegel.llama-swap.managed=true` labels → remote_write → VictoriaMetrics (TrueNAS). VictoriaMetrics chosen over Prometheus: native remote_write receiver at `/api/v1/write`, PromQL-compatible, one tiny container.
- **Logs**: Alloy `loki.source.docker` (via docker.sock) tails litellm, llama-swap, and managed vLLM backend containers → Loki (TrueNAS), 30d retention.
- **Traces**: LiteLLM `otel` callback → OTLP http to Alloy :4318 (inference box) → forwarded → Tempo (TrueNAS). The local relay gives one egress/batch/retry point and keeps LiteLLM pointing at a stable localhost-adjacent endpoint.

## Approach

### Step 1 — TrueNAS storage stack: `services/observability/`

New stack dir with (all new files; no equivalent exists in repo):

- `services/observability/docker-compose.yml` — git-sync sidecar (copy the sidecar verbatim from `services/xberg/docker-compose.yml` lines 12–52: same image digest, sparse-checkout config naming `/services/observability/`, healthcheck checking `test -f /git/current/services/observability/loki/config.yaml`), named volume `observability-config:/git`, then four services on network `name: observability`, each with `restart: unless-stopped`, `init: true`, `user: "0:0"` (bind-mount dirs are root-owned; simplest fix per TrueNAS stacks), no resource limits needed:
  - `grafana` — `grafana/grafana:12.3.1`; `container_name: observability-grafana`; ports `"192.168.1.39:3000:3000"`; env `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:?Set GRAFANA_ADMIN_PASSWORD in Portainer}`, `GF_ANALYTICS_REPORTING_ENABLED=false`, `GF_NEWSFEEDS_ENABLED=false`, `GF_PATHS_PROVISIONING=/grafana/current/services/observability/grafana/provisioning`; volumes `observability-config:/grafana:ro`, `/mnt/tank/container-configs/observability/grafana:/var/lib/grafana`; depends_on git-sync healthy.
  - `victoriametrics` — `victoriametrics/victoria-metrics:v1.115.0`; container_name `observability-victoriametrics`; command `["-storageDataPath=/victoria-metrics-data", "-retentionPeriod=90d", "-httpListenAddr=:8428"]`; ports `"192.168.1.39:8428:8428"`; volume `/mnt/tank/container-configs/observability/victoriametrics:/victoria-metrics-data`.
  - `loki` — `grafana/loki:3.4.2`; container_name `observability-loki`; command `["-config.file=/grafana/current/services/observability/loki/config.yaml", "-config.expand-env=true"]`; ports `"192.168.1.39:3100:3100"`; volume `/mnt/tank/container-configs/observability/loki:/loki`.
  - `tempo` — `grafana/tempo:2.9.0`; container_name `observability-tempo`; command `["-config.file=/grafana/current/services/observability/tempo/config.yaml"]`; ports `"192.168.1.39:4317:4317"`, `"192.168.1.39:4318:4318"`, `"192.168.1.39:3200:3200"`; volume `/mnt/tank/container-configs/observability/tempo:/var/tempo`.
  - Header comment: Portainer CE stack, environment = the TrueNAS environment (the one hosting mealie/babybuddy/hermes, named `truenas`), repo `mspiegel31/home-services`, ref main, path `services/observability/docker-compose.yml`, poll 5 min. Data dirs follow the repo rule `/mnt/tank/container-configs/<APP_NAME>`. Secrets (`GRAFANA_ADMIN_PASSWORD`) via Portainer UI, declared as `${VAR}` — never `env_file` (repo rule).
  - TrueNAS port sanity: 3000/3100/3200/4317/4318/8428 not used by repo TrueNAS stacks (9000/9001/9119). k3s uses 6443/10250/8472 — no overlap.

- `services/observability/loki/config.yaml`:
  ```yaml
  auth_enabled: false
  server: { http_listen_port: 3100, grpc_listen_port: 9096 }
  common:
    instance_addr: 127.0.0.1
    path_prefix: /loki
    replication_factor: 1
    ring: { kvstore: { store: inmemory } }
    storage: { filesystem: { chunks_directory: /loki/chunks, rules_directory: /loki/rules } }
  schema_config:
    configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: filesystem
        schema: v13
        index: { prefix: index_, period: 24h }
  compactor:
    working_directory: /loki/compactor
    retention_enabled: true
    delete_request_store: filesystem
  limits_config:
    retention_period: 720h
    retention_stream:
      - selector: '{job="vllm"}'
        priority: 1
  ruler: { storage: { type: local, local: { directory: /loki/rules } } }
  ```

- `services/observability/tempo/config.yaml`:
  ```yaml
  server: { http_listen_port: 3200, grpc_listen_port: 9095 }
  distributor:
    receivers:
      otlp:
        protocols:
          grpc: { endpoint: "0.0.0.0:4317" }
          http: { endpoint: "0.0.0.0:4318" }
  ingester: { trace_idle_period: 10s, max_block_duration: 1h }
  compactor: { compaction: { block_retention: 168h, compacted_block_retention: 1h } }
  metrics_generator:
    registry: { collection_interval: 15s }
    storage:
      path: /var/tempo/generator/wal
      remote_write: { url: "http://victoriametrics:8428/api/v1/write", send_exemplars: false }
    processors: [ service_graphs, span_metrics ]
  overrides:
    metrics_generator: { processors: [service_graphs, span_metrics] }
  storage:
    trace:
      backend: local
      local: { path: /var/tempo/traces, max_compaction_objects: 1000000 }
      wal: { path: /var/tempo/wal }
  ```

- `services/observability/grafana/provisioning/datasources/observability.yaml` — three datasources with explicit stable uids: `Metrics` (type prometheus, uid `vm`, url `http://victoriametrics:8428`, isDefault, `jsonData: { httpMethod: GET, timeInterval: 15s }`), `Logs` (type loki, uid `loki`, url `http://loki:3100`), `Traces` (type tempo, uid `tempo`, url `http://tempo:3200`, `jsonData: { tracesToLogsV2: { datasourceUid: loki }, serviceMap: { datasourceUid: vm }, nodeGraph: { enabled: true }, lokiSearch: { datasourceUid: loki } }`).
- `services/observability/grafana/provisioning/dashboards/inference.yaml` — file provider, folder `Inference`, `options.path: /grafana/current/services/observability/grafana/dashboards`.
- `services/observability/grafana/dashboards/inference.json` — authored in Step 5 (needs real metric names confirmed). Step 1 ships it as a minimal valid dashboard: `{"uid":"inference","title":"Inference","schemaVersion":39,"panels":[]}` so provisioning succeeds.

Deploy TrueNAS stack; verify: `curl -fsS http://192.168.1.39:8428/health` → `OK`; `curl -fsS http://192.168.1.39:3100/ready` → `Ready`; `curl -fsS http://192.168.1.39:3200/ready`; Grafana login works.

### Step 2 — Inference-box collector: `services/inference-telemetry/`

New stack (git-sync sidecar pattern again; sparse checkout `/services/inference-telemetry/`; healthcheck checks `test -f /git/current/services/inference-telemetry/config.alloy`):

- `services/inference-telemetry/docker-compose.yml`:
  - `name: inference-telemetry`; network `telemetry` (name: inference-telemetry) plus the **external** existing network `llama-swap-vllm-backend` (name: llama-swap-vllm-backend) so Alloy resolves backend container names (`vllm-*`) by docker DNS.
  - `alloy` — `grafana/alloy:v1.14.1`; `container_name: inference-telemetry-alloy`; command `["run", "/config/current/services/inference-telemetry/config.alloy", "--storage.path=/var/lib/alloy/data"]`; volumes: `inference-telemetry-config:/config:ro`, `alloy-data:/var/lib/alloy/data`, `/var/run/docker.sock:/var/run/docker.sock:ro`? — **rw not needed, `:ro` sufficient for logs API; docker_sd + loki.source.docker work read-only**. Ports `"4318:4318"` (host publish; LiteLLM reaches `http://192.168.1.98:4318`). Env: `LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY:?Set LITELLM_MASTER_KEY in Portainer}`, `LLAMA_SWAP_API_KEY=${LLAMA_SWAP_API_KEY:?Set LLAMA_SWAP_API_KEY in Portainer}`, `SHIP_ENDPOINT=${SHIP_ENDPOINT:?Set SHIP_ENDPOINT in Portainer, e.g. http://192.168.1.39}` (endpoint host injected as env, never baked into git-synced config — repo is public). depends_on git-sync healthy. Healthcheck `["CMD", "wget", "-qO-", "http://127.0.0.1:12345/-/ready"]` with Alloy `http { listen_port = 12345 }` in the config.
  - Header comment: deploy to the same Portainer environment as `services/litellm` / `services/llama-swap-vllm` (inference box).

- `services/inference-telemetry/config.alloy` — full contents (exact; Alloy exposes `env("VAR")`):
  ```alloy
  http { listen_port = 12345 }
  logging { level = "info" }

  const { ship = env("SHIP_ENDPOINT") }

  discovery.docker "all" { host = "unix:///var/run/docker.sock" }

  // metrics targets: managed vLLM backends, addressed by container name on
  // llama-swap-vllm-backend, model label from the existing io.mspiegel label.
  discovery.relabel "vllm" {
    targets = discovery.docker.all.targets
    rule { action = "keep", source_labels = ["__meta_docker_container_label_io_mspiegel_llama_swap_managed"], regex = "true" }
    rule { action = "replace", source_labels = ["__meta_docker_container_name"], regex = "/(.*)", target_label = "__address__", replacement = "$1:8000" }
    rule { action = "replace", source_labels = ["__meta_docker_container_label_io_mspiegel_llama_swap_model"], target_label = "model" }
    rule { action = "labelmap", regex = "__meta_docker_container_label_io_mspiegel_llama_swap_model", target_label = "model" }
    rule { action = "replace", replacement = "vllm", target_label = "job" }
  }
  ```
  Note: the `keep` rule must run on the raw discovery targets, the `__address__` rewrite after; if the pinned Alloy rejects `keep` after `replace` ordering, order rules keep→replace as written (they are evaluated in order — the block above is already correct).
  ```alloy
  discovery.relabel "logs" {
    targets = discovery.docker.all.targets
    rule { action = "replace", source_labels = ["__meta_docker_container_name"], regex = "/(.*)", target_label = "container" }
    rule { action = "replace", source_labels = ["__meta_docker_container_label_com_docker_compose_project"], target_label = "app" }
    rule { action = "replace", source_labels = ["__meta_docker_container_label_io_mspiegel_llama_swap_model"], target_label = "model" }
    rule { action = "replace", replacement = "litellm", target_label = "job" }
    rule { action = "labeldrop", regex = "__meta.*" }
    rule { action = "keep", source_labels = ["app"], regex = "litellm|llama-swap-vllm" }
    rule { action = "keep", source_labels = ["model"], regex = ".+" }
  }
  ```
  The two `keep` rules above are ANDed by Prometheus relabel semantics; to accept compose-project containers **OR** managed vllm backends, implement with `action = "keep"` on a joined label: add first `rule { action = "replace", source_labels = ["app","model"], separator = ";", target_label = "keepme" }` then `rule { action = "keep", source_labels = ["keepme"], regex = "(litellm|llama-swap-vllm);.*|;.+" }` and `rule { action = "labeldrop", regex = "keepme" }` — use this joined-key form, it is exact.

  ```alloy
  prometheus.scrape "litellm" {
    targets      = [{ "__address__" = "192.168.1.98:4000", "job" = "litellm" }]
    scheme       = "http"
    authorization = { type = "Bearer", credentials = env("LITELLM_MASTER_KEY") }
    scrape_interval = "15s"
    forward_to   = [prometheus.remote_write.truenas.receiver]
  }
  prometheus.scrape "llama_swap" {
    targets      = [{ "__address__" = "192.168.1.98:11437", "job" = "llama-swap" }]
    scheme       = "http"
    scrape_interval = "15s"
    forward_to   = [prometheus.remote_write.truenas.receiver]
  }
  prometheus.scrape "vllm_backends" {
    targets         = discovery.relabel.vllm.output
    scrape_interval = "15s"
    forward_to      = [prometheus.remote_write.truenas.receiver]
  }
  prometheus.remote_write "truenas" {
    endpoint { url = concat(const.ship, ":8428/api/v1/write") }
  }

  loki.source.docker "applogs" {
    host       = "unix:///var/run/docker.sock"
    targets    = discovery.relabel.logs.output
    forward_to = [loki.write.truenas.receiver]
  }
  loki.write "truenas" {
    endpoint { url = concat(const.ship, ":3100/loki/api/v1/push") }
  }

  otelcol.receiver.otlp "in" {
    http { endpoint = "0.0.0.0:4318" }
    traces { output = [otelcol.processor.batch.trues.receiver] }
  }
  otelcol.processor.batch "trues" {
    output = [otelcol.exporter.otlphttp.truenas.input]
  }
  otelcol.exporter.otlphttp "truenas" {
    client { endpoint = concat(const.ship, ":4318") }
  }
  ```
  (`const.ship` = `http://192.168.1.39`; `concat` is valid Alloy string function. vLLM metric label: vLLM emits label `model_name` (from `--served-model-name` = model id); the relabel `model` label on targets is the join key across jobs; keep both.)

Deploy. Verify before touching litellm:
- `docker exec inference-telemetry-alloy wget -qO- http://192.168.1.98:11437/metrics | grep -c llamaswap_` → >0 (if 401: add `authorization { credentials = env("LLAMA_SWAP_API_KEY") }` to that scrape block — route is registered on the gin root engine, expected unauthenticated).
- Wake a model: `curl -s http://192.168.1.98:11437/v1/chat/completions -H "Authorization: Bearer $LLAMA_SWAP_API_KEY" -H 'Content-Type: application/json' -d '{"model":"swift-1.5-fp8","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'`, then `curl -sG 'http://192.168.1.39:8428/api/v1/query' --data-urlencode 'query=count by (model) (vllm:generation_tokens_total)'` → non-empty, model = `swift-1.5-fp8`.
- Also capture the exact vLLM metric families for Step 5: `docker exec inference-telemetry-alloy wget -qO- http://vllm-swift-1-5-fp8:8000/metrics | grep -oE '^vllm:[a-z_]+' | sort -u` → record output; Step 5 panel queries use these names (expected: `vllm:generation_tokens_total`, `vllm:prompt_tokens_total`, `vllm:time_to_first_token_seconds`, `vllm:inter_token_latency_seconds`, `vllm:gpu_cache_usage_perc`, `vllm:num_requests_running`, `vllm:num_requests_waiting`, `vllm:spec_decode_draft_acceptance_rate`, `vllm:spec_decode_efficiency`; if the pinned vLLM uses `vllm:request_success_total`-style naming that differs, adjust panels to what this grep prints).
- Logs: `curl -sG 'http://192.168.1.39:3100/loki/api/v1/query' --data-urlencode 'query=count (count_over_time({job="litellm"}[5m]))'` → non-empty.

### Step 3 — LiteLLM Prometheus metrics (gateway tok/s)

`services/litellm/config.yaml`, in `litellm_settings:` (line ~71), extend the existing callbacks list and add the stream label:
```yaml
  callbacks:
    - custom_callbacks.local_thinking_policy
    - prometheus
    - otel
  prometheus_emit_stream_label: true
```
(`prometheus` needs `prometheus_client`, preinstalled in the litellm docker image per LiteLLM Prometheus docs; keep `cache`/`cache_params` untouched; callback ordering after `local_thinking_policy` preserves the thinking translation.)

Restart the `litellm` service (config change requires restart; repo convention). No llama-swap change needed: its `performance.enable` defaults true and the router container already has a GPU reservation "so in-container nvidia-smi works for /metrics" — GPU/system metrics ship without config edits.

Verify: `curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://192.168.1.98:4000/metrics | grep -c litellm_` → >0; after one chat completion through :4000, `curl -sG 'http://192.168.1.39:8428/api/v1/query' --data-urlencode 'query=sum by (requested_model) (rate(litellm_output_tokens_metric_total[5m]))'` → series for the requested model.

### Step 4 — LiteLLM traces → Tempo

`services/litellm/docker-compose.yml`, `litellm` service `environment:` add:
```yaml
      OTEL_EXPORTER_OTLP_ENDPOINT: http://192.168.1.98:4318
      OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
      OTEL_SERVICE_NAME: litellm-proxy
      USE_OTEL_LITELLM_REQUEST_SPAN: "true"
      OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT: SPAN_ONLY
```
(`otel` callback added in Step 3 reads these; `USE_OTEL_LITELLM_REQUEST_SPAN` gives a clean per-request span; SPAN_ONLY keeps prompts on spans for Tempo trace debugging — LAN-only storage, Loki already holds prompt-bearing logs. Endpoint is the inference-box Alloy relay, published :4318 in Step 2.)

Verify: `docker exec litellm python -c "import opentelemetry.sdk, opentelemetry.exporter.otlp.proto.http.trace_exporter"` succeeds (image ships OTel SDK; if it fails, build `images/litellm/Dockerfile` = `FROM docker.litellm.ai/berriai/litellm:main-stable` + `RUN pip install --no-cache-dir opentelemetry-sdk opentelemetry-exporter-otlp-proto-http`, CI pattern per `images/vllm-fastokens/Dockerfile`, switch compose image). Then send one chat completion through :4000; Tempo search (`curl -sG 'http://192.168.1.39:3200/tempo/api/search' --data-urlencode tags=service.name=litellm-proxy -d limit=1` → JSON with a trace id) and Grafana Explore→Traces shows a span named `Received Proxy Server Request` (exact LiteLLM root span name) with child `litellm_request`.

### Step 5 — Dashboard content

Replace the placeholder `services/observability/grafana/dashboards/inference.json` with timeseries panels, datasource uid `vm` (all queries; `$__rate_interval` for ranges; add a `model` template variable: `label_values(vllm:generation_tokens_total, model)`, applied via `{model=~"$model"}` where the label exists):

1. Gateway output tok/s per model — `sum by (requested_model) (rate(litellm_output_tokens_metric_total{stream="True"}[$__rate_interval]))`
2. Gateway total tok/s (in+out) per model — `sum by (requested_model) (rate(litellm_total_tokens_metric_total[$__rate_interval]))`
3. Engine decode tok/s per model — `sum by (model) (rate(vllm:generation_tokens_total[$__rate_interval]))`
4. Engine prefill tok/s per model — `sum by (model) (rate(vllm:prompt_tokens_total[$__rate_interval]))`
5. TTFT p95 — `histogram_quantile(0.95, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[$__rate_interval])))`
6. Inter-token latency p95 — `histogram_quantile(0.95, sum by (le) (rate(vllm:inter_token_latency_seconds_bucket[$__rate_interval])))`
7. Spec-decode acceptance — `avg by (model) (vllm:spec_decode_draft_acceptance_rate)`
8. KV cache usage — `max by (model) (vllm:gpu_cache_usage_perc)`
9. Running/waiting requests — `max by (model) (vllm:num_requests_running)` and `max by (model) (vllm:num_requests_waiting)` (two queries, one panel)
10. GPU util / VRAM / power (router nvidia-smi) — `llamaswap_gpu_util_percent`, `llamaswap_gpu_memory_used_bytes`, `llamaswap_gpu_power_draw_watts`
11. Gateway p95 e2e latency — `histogram_quantile(0.95, sum by (le) (rate(litellm_request_total_latency_metric_bucket[$__rate_interval])))`
12. Request rate / failures — `sum by (requested_model) (rate(litellm_proxy_total_requests_metric_total[$__rate_interval]))`, `sum by (requested_model, exception_class) (rate(litellm_proxy_failed_requests_metric_total[$__rate_interval]))`

Author as one row per group, `type: "timeseries"`, `datasource: {"type":"prometheus","uid":"vm"}`; counters use the `_total`-suffixed sample (Prometheus python client emits `_created` — ignore it). Metric-name confirmation from Step 2 is load-bearing: rename any panel query to the names that grep printed.

Verify end-to-end (the tok/s acceptance): send a long-output request through LiteLLM (`{"model":"swift-1.5-fp8","messages":[{"role":"user","content":"Count from 1 to 500, one number per line."}],"max_tokens":1024,"stream":true}`), then within one scrape interval Grafana "Inference" panels 1,3,4 rise above zero for `swift-1.5-fp8`; Grafana Explore → Logs `{app="llama-swap-vllm"}` shows the backend load log; Explore → Traces opens the request span. Also set the existing glance tile: Portainer env for the glance stack `GRAFANA_URL=http://192.168.1.39:3000` (tile at `services/glance/config/home.yml` line 35 already reads it).

## Critical files & anchors

- `services/xberg/docker-compose.yml:12-52` — canonical git-sync sidecar to copy (sparse-checkout config, healthcheck style).
- `services/llama-swap-vllm/docker-compose.yml:80-109` — router ports/GPU-reservation/external-network facts the collector depends on.
- `services/llama-swap-vllm/config.yaml:23-33` — `DOCKER_PREFIX` labels `io.mspiegel.llama-swap.managed=true` / `.model=${MODEL_ID}`: the docker-sd join keys.
- `services/litellm/config.yaml:71-81` — `litellm_settings.callbacks` insertion point.
- `services/glance/config/home.yml:35-37` — Grafana tile reading `${GRAFANA_URL}`.

## Assumptions & contingencies

- Portainer env names: TrueNAS env (`truenas`) hosts `services/observability`; the inference-box env hosts `inference-telemetry` beside litellm. If the TrueNAS Portainer env is not the box at 192.168.1.39, deploy there and set bind paths/ships to that host.
- Image versions above are the pins to write; if a tag doesn't exist at implementation time, pin the newest patch of the same minor (Alloy stays on v1.x; `discovery.docker`, `loki.source.docker`, `otelcol.receiver.otlp` are stable v1 APIs).
- llama-swap `/metrics` expected unauthenticated (root gin route); on 401 add the `LLAMA_SWAP_API_KEY` bearer to that scrape job.
- vLLM `/metrics` is enabled by default in `vllm/vllm-openai` (no engine flag) — confirm from Step 2's scrape; if a backend serves no `/metrics`, that model's engine panels stay empty and no engine flag is added (do not edit 14 model files for metrics).
- TrueNAS bind dirs: create `/mnt/tank/container-configs/observability/{grafana,victoriametrics,loki,tempo}` before deploy (TrueNAS host UI/CLI, not a repo change).
- LiteLLM OTel SDK present in `main-stable` image [unverified — confirm first]; fallback = the derived image in Step 4.
- vLLM metric name spelling for v0.29/0.30 [unverified — confirm first via the Step 2 grep]; panels take the observed names, nothing else changes.
