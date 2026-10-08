#!/usr/bin/env python3
"""Prometheus exporter for the Strata engine (github.com/Niko1221/Strata).

Strata's own GET /metrics is JSON for its Monitor tab, so Alloy's
prometheus.scrape of the managed backend containers cannot read it.  This
serves Prometheus text on EXPORTER_PORT (8000, where the vllm_backends scrape
looks) and translates the JSON it fetches from the engine on PORT (8080).

Metrics keep vLLM's names where the meaning is the same, so the inference
dashboard's throughput, running/waiting and draft-acceptance panels pick the
lane up; Strata-only facts use a strata_ prefix.  There is no source for the
TTFT/ITL histograms or kv_cache_usage_perc, so they are not exported.
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT") or 8080)
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT") or 8000)
ENGINE_METRICS = f"http://127.0.0.1:{PORT}/metrics"
FETCH_TIMEOUT_S = 3.0


def number(value):
    """A metric value, or None when the engine did not report it."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def divide(top, bottom):
    top, bottom = number(top), number(bottom)
    return None if top is None or bottom in (None, 0) else top / bottom


def collect(payload):
    """(name, type, value) lines, plus the labeled state gauge."""
    totals = payload.get("totals") or {}
    live = payload.get("live") or {}
    newest = next(iter(payload.get("requests") or []), {}) or {}

    state = live.get("state")
    running = number(live.get("running"))
    if running is None:
        running = 1 if state in ("reading", "generating") else 0

    series = [
        ("strata_up", "gauge", 1),
        ("vllm:generation_tokens_total", "counter", number(totals.get("output_tokens"))),
        ("vllm:prompt_tokens_total", "counter", number(totals.get("prompt_tokens"))),
        ("vllm:num_requests_running", "gauge", running),
        ("vllm:num_requests_waiting", "gauge", number(live.get("queued"))),
        ("vllm:spec_decode_draft_acceptance_rate", "gauge",
         divide(totals.get("drafts_accepted"), totals.get("drafts_offered"))),
        ("strata_requests_total", "counter", number(totals.get("requests"))),
        ("strata_prompt_tokens_reused_total", "counter", number(totals.get("reused"))),
        ("strata_spec_decode_drafts_offered_total", "counter", number(totals.get("drafts_offered"))),
        ("strata_spec_decode_drafts_accepted_total", "counter", number(totals.get("drafts_accepted"))),
        ("strata_prompt_seconds_total", "counter", divide(totals.get("prompt_ms"), 1000)),
        ("strata_decode_seconds_total", "counter", divide(totals.get("decode_ms"), 1000)),
        ("strata_expert_cache_hit_rate", "gauge", number(newest.get("hit_rate"))),
        ("strata_expert_pcie_share", "gauge", number(newest.get("pcie_share"))),
        ("strata_last_decode_tokens_per_second", "gauge", number(newest.get("decode_tok_s"))),
    ]
    if isinstance(state, str) and state:
        series.append(("strata_state", "gauge", 1, {"state": state}))
    return series


def render(series):
    out = []
    for entry in series:
        name, kind, value = entry[0], entry[1], entry[2]
        labels = entry[3] if len(entry) > 3 else None
        if value is None:
            continue
        out.append(f"# TYPE {name} {kind}")
        if labels:
            rendered = ",".join(f'{k}="{v}"' for k, v in labels.items())
            out.append(f"{name}{{{rendered}}} {value}")
        else:
            out.append(f"{name} {value}")
    return "\n".join(out) + "\n"


def scrape():
    try:
        with urllib.request.urlopen(ENGINE_METRICS, timeout=FETCH_TIMEOUT_S) as response:
            if response.status != 200:
                raise urllib.error.HTTPError(ENGINE_METRICS, response.status, "not 200", response.headers, None)
            payload = json.loads(response.read().decode("utf-8", "replace"))
        if not isinstance(payload, dict):
            raise ValueError("engine metrics is not an object")
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        # Normal while setup downloads the model or the engine loads it.
        return render([("strata_up", "gauge", 0)])
    return render(collect(payload))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802 (http.server's interface)
        if self.path.split("?")[0] != "/metrics":
            self.send_error(404)
            return
        body = scrape().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 (http.server's parameter name)
        del format, args


def main():
    ThreadingHTTPServer(("0.0.0.0", EXPORTER_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
