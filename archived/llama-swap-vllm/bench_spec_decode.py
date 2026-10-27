#!/usr/bin/env python3
"""Spec-decode / prefix-cache bench for the qwen3.8-27b-fp8 lane.

9.6k-token shared prefix plus a free-form prose instruction, streamed so TTFT
(prefill + queue) and decode rate are separable, and acceptance-sensitive enough
to compare draft heads. Run it inside the backend network — it talks to vLLM
directly, since LiteLLM drops unknown params and caches responses:

    docker run --rm --network llama-swap-vllm-backend \\
      -v "$PWD/bench_spec_decode.py:/bench.py:ro" \\
      ghcr.io/mspiegel31/vllm-fastokens:latest python3 /bench.py <label>

Prints one JSON object. Compare decode_tps across configs; read the engine's own
SpecDecoding metrics line for mean acceptance length. The cold arm is forced by
a session nonce at the head of the prompt (it invalidates every later block),
but see BENCHMARKS.md — under shared production load only the first cold run
after a config change is trustworthy.
"""

import json
import random
import statistics
import sys
import time
import urllib.request

BASE = "http://vllm-qwen3-8-27b-fp8:8000/v1/chat/completions"
INSTRUCTION = "\nWrite about 250 words on how ocean currents move heat around the planet."


def stream(prompt, max_tokens, temperature=0.7):
    body = {
        "model": "qwen3.8-27b-fp8",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    ttft = None
    usage = {}
    with urllib.request.urlopen(req, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if event.get("usage"):
                usage = event["usage"]
            if ttft is None and event.get("choices") and (event["choices"][0].get("delta") or {}).get("content"):
                ttft = time.perf_counter() - started
    total = time.perf_counter() - started
    completion = usage.get("completion_tokens") or 0
    decode = total - (ttft or 0)
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": completion,
        "ttft": round(ttft or 0, 2),
        "total": round(total, 2),
        "decode_tps": round(completion / decode, 1) if decode > 0 else None,
        "effective_tps": round(completion / total, 1),
    }


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    random.seed(4242)
    prefix = "Reference table of seven-digit ids:\n" + " ".join(
        f"{random.randrange(1000000, 9999999)}" for _ in range(1200)
    )
    stream(prefix + "\nReply with the single word: ready", 1)  # warm the prefix
    warm = [stream(prefix + INSTRUCTION, 320) for _ in range(3)]
    cold_prompt = f"Session {random.randrange(10**9)}.\n{prefix}{INSTRUCTION}"
    cold = stream(cold_prompt, 320)
    print(
        json.dumps(
            {
                "label": label,
                "cached": {
                    "ttft": [r["ttft"] for r in warm],
                    "total": [r["total"] for r in warm],
                    "decode_tps": [r["decode_tps"] for r in warm],
                    "effective_tps": [r["effective_tps"] for r in warm],
                    "completion_tokens": [r["completion_tokens"] for r in warm],
                    "median_ttft": round(statistics.median(r["ttft"] for r in warm), 2),
                    "median_decode_tps": round(statistics.median(r["decode_tps"] for r in warm), 1),
                },
                "cold": cold,
            },
            indent=2,
        )
    )


main()
