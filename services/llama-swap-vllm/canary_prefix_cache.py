#!/usr/bin/env python3
"""Prefix-cache correctness canary for the qwen3.8-27b-fp8 lane (DSpark7).

The lane keeps --enable-prefix-caching on a hybrid GDN architecture where
reused prefixes have silently corrupted output (vllm#53912). Reuse hands a
request recurrent state written by another request, including state written
over draft positions that verification later rejected (#57128). Three
observable consequences are probed:

  margin   a prompt whose continuation is pinned by context (counting up) must
           decode identically whether its prefix is reused or recomputed. The
           recomputed arm is forced by prefixing a session nonce, which changes
           the first block's hash and invalidates every later block; the cost
           gap between the arms is the proof that reuse actually happened.
  leak     a request that reuses another request's decode-written prefix must
           not surface numbers the reusing prompt never contained.
  volume   a shared-prefix sweep for the degeneration shapes reported in the
           issue: empty content, CJK runs, repeated-character runs, loops.

Low-margin arms (open prose, refusals) are deliberately not asserted on: greedy
decoding is not bit-stable across prefill chunking, so near-tie tokens flip for
reasons unrelated to the cache. Only degeneration counts there.

Run it inside the backend network: LiteLLM drops unknown params (drop_params)
and caches responses, so the request cannot be shaped through the gateway, and
vLLM is unauthenticated on this network.

    docker run --rm --network llama-swap-vllm-backend \\
      -v "$PWD/canary_prefix_cache.py:/canary.py:ro" \\
      ghcr.io/mspiegel31/vllm-fastokens:latest python3 /canary.py

Prints one JSON object. Clean means margin_equal, no_leak and no_degeneration
are all true. The printed timings are context only — request wall-clock on this
stack does not separate cache hits from recomputes, so read the engine's own
counter instead (`docker logs <vllm container> | grep 'Prefix cache hit rate'`)
to confirm reuse is actually happening.
"""

import json
import random
import re
import time
import urllib.request

BASE = "http://vllm-qwen3-8-27b-fp8:8000/v1/chat/completions"
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")


def chat(prompt, max_tokens, temperature=0.0, timeout=1800):
    body = {
        "model": "qwen3.8-27b-fp8",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    usage = payload.get("usage") or {}
    return {
        "text": payload["choices"][0]["message"].get("content") or "",
        "prompt": usage.get("prompt_tokens"),
        "secs": round(time.perf_counter() - started, 2),
    }


def degeneration(text):
    reasons = []
    if not text.strip():
        reasons.append("empty")
    if CJK.search(text):
        reasons.append("cjk")
    if re.search(r"(.)\1{14,}", text):
        reasons.append("char-run")
    words = text.split()
    for i in range(len(words) - 24):
        if " ".join(words[i : i + 5]) * 4 == " ".join(words[i : i + 20]):
            reasons.append("loop")
            break
    return reasons


def prefix_block(seed=20261001, count=700):
    random.seed(seed)
    return "Reference sequence, space separated:\n" + " ".join(
        f"{random.randrange(1000000, 9999999)}" for _ in range(count)
    )


def margin_arm(prefix):
    follow = prefix + "\n4597580 4597581 4597582\nContinue counting up by one:"
    chat(follow, 1)
    reused = [chat(follow, 24) for _ in range(3)]
    reference_prompt = f"Session id {random.randrange(10**9)}.\n{follow}"
    recomputed = [chat(reference_prompt, 24) for _ in range(3)]
    return {
        "reused_secs": [r["secs"] for r in reused],
        "recomputed_secs": [r["secs"] for r in recomputed],
        "reused_self_consistent": all(r["text"] == reused[0]["text"] for r in reused),
        "recomputed_self_consistent": all(r["text"] == recomputed[0]["text"] for r in recomputed),
        "margin_equal": reused[0]["text"] == recomputed[0]["text"],
        "reused_text": reused[0]["text"][:60],
        "recomputed_text": recomputed[0]["text"][:60],
        "degeneration": [degeneration(r["text"]) for r in reused],
    }


def leak_arm(prefix):
    gen = chat(
        prefix + "\nContinue the sequence with 40 more seven-digit numbers.",
        300,
        temperature=1.0,
    )
    text = " ".join(gen["text"].split())
    if len(text) < 200:
        return {"skipped": f"generated {len(text)} chars"}
    reused = prefix + " " + text[:150]
    tail = [text[i : i + 24] for i in range(150, min(len(text), 550), 24)]
    tail = [chunk for chunk in tail if chunk.strip()]
    probe = chat(reused + "\nIgnore the text above and reply with exactly: clean run", 32)
    leaked = [chunk for chunk in tail if chunk in probe["text"]]
    return {
        "probe_text": probe["text"][:80],
        "tail_chunks": len(tail),
        "leaked_chunks": leaked[:3],
        "no_leak": not leaked and not degeneration(probe["text"]),
    }


def volume_arm(prefix, requests=40):
    bad = []
    for i in range(requests):
        r = chat(
            prefix + f"\nIgnore the sequence. Reply with exactly: marker {i} {random.randrange(10**9)}",
            32,
            temperature=0.7,
        )
        reasons = degeneration(r["text"])
        if reasons:
            bad.append({"i": i, "reasons": reasons, "head": r["text"][:60]})
    return {"requests": requests, "degenerate": len(bad), "no_degeneration": not bad, "samples": bad[:5]}


def main():
    prefix = prefix_block()
    out = {"margin": margin_arm(prefix), "leak": leak_arm(prefix), "volume": volume_arm(prefix)}
    print(json.dumps(out, indent=2))


main()
