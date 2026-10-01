#!/bin/bash
# Deterministic checks for the LFM2.5 text lane task. Stdlib-only Python.
# The model is NOT a local reasoning model, so the correct behavior is to wire
# llama-swap + litellm only and leave custom_callbacks.py untouched.
python3 - <<'PYEOF'
import json, re, subprocess, sys
from pathlib import Path

ID = "lfm2.5-8b-text"
CP = "LiquidAI/LFM2.5-8B-Text"

checks = []
def add(name, passed, msg=""):
    checks.append({"name": name, "passed": bool(passed), "message": msg})

def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace") if Path(p).exists() else ""

# --- llama-swap backend file ------------------------------------------------
ls_path = f"services/llama-swap-vllm/models/{ID}.yaml"
ls = read(ls_path)
add("llama-swap-model-file", bool(ls.strip()), ls_path)
if ls:
    add("ls-model-id-key", re.search(r'^\s*"%s":' % re.escape(ID), ls, re.M) is not None, "models: key for the id")
    add("ls-checkpoint", CP in ls, f"checkpoint macro must be {CP}")
    name = re.search(r"--name\s+(\S+)", ls)
    proxy = re.search(r"proxy:\s*http://([^/:]+):\d+", ls)
    stop = re.search(r"cmdStop:\s*docker stop --time \d+\s+(\S+)", ls)
    vals = {g.group(1) for g in (name, proxy, stop) if g}
    consistent = len(vals) == 1 and "lfm" in next(iter(vals), "")
    add("ls-container-consistent", consistent, f"--name/proxy/cmdStop = {sorted(vals)}")
    add("ls-text-only", re.search(r"in:\s*\[\s*\"?text\"?\s*\]", ls) is not None, "capabilities.in is text-only")
    add("ls-no-vision", "image" not in ls.split("capabilities", 1)[1].split("proxy", 1)[0], "no vision in capabilities")
    add("ls-tools-true", re.search(r"tools:\s*true", ls) is not None, "capabilities.tools true")
    add("ls-no-trust-remote-code", "--trust-remote-code" not in ls, "must not load remote code")
    add("ls-no-spec-decode", "speculative-config" not in ls and "--speculative" not in ls, "no spec decode")
    add("ls-no-qwen-macro", "QWEN38_COMMON" not in ls, "Qwen38-only macro must not leak into a non-Qwen cmd")
    add("ls-no-reasoning-parser", "reasoning-parser" not in ls, "no Qwen reasoning parser on a non-reasoning model")

# --- llama-swap routing ------------------------------------------------------
lsconf = read("services/llama-swap-vllm/config.yaml")
m = re.search(r"co-resident:\s*\"([^\"]+)\"", lsconf)
add("ls-routing-set", m is not None and ID in m.group(1), "id present in the co-resident routing set")

# --- litellm deployment ------------------------------------------------------
lt_path = f"services/litellm/models/{ID}.yaml"
lt = read(lt_path)
add("litellm-model-file", bool(lt.strip()), lt_path)
if lt:
    add("lt-model-name", re.search(r"model_name:\s*%s\b" % re.escape(ID), lt) is not None, "model_name matches the id")
    add("lt-api-base", "http://192.168.1.98:11437/v1" in lt, "llama-swap api_base with /v1")
    add("lt-provider", "hosted_vllm" in lt, "custom_llm_provider hosted_vllm")
    add("lt-func-calling", re.search(r"supports_function_calling:\s*true", lt) is not None, "supports_function_calling")
    add("lt-no-reasoning-meta", not re.search(r"\breasoning:\s*true|supports_reasoning:\s*true|reasoning_effort:", lt),
        "no reasoning metadata on a non-reasoning model")
ltconf = read("services/litellm/config.yaml")
add("lt-include", f"models/{ID}.yaml" in ltconf, "file listed in litellm include")

# --- callback untouched ------------------------------------------------------
cb = read("services/litellm/custom_callbacks.py")
add("cb-untouched", ID not in cb, "non-reasoning model must not be added to LocalReasoningModel")
cb_test = read("services/litellm/test_custom_callbacks.py")
add("cb-test-untouched", ID not in cb_test, "no new callback test for a non-reasoning model")
try:
    r = subprocess.run([sys.executable, "test_custom_callbacks.py"], cwd="services/litellm",
                       capture_output=True, text=True, timeout=60)
    out = (r.stdout or "") + (r.stderr or "")
    # unittest writes its summary to stderr; trust the exit code and the OK line.
    suite_ok = r.returncode == 0 and "OK" in out
    add("cb-suite-passes", suite_ok, out.strip().splitlines()[-1] if out.strip() else "no output")
except Exception as e:
    add("cb-suite-passes", False, f"failed to run: {e}")

passed = sum(c["passed"] for c in checks)
print(json.dumps({
    "score": passed / len(checks),
    "details": f"{passed}/{len(checks)} lfm2.5-8b-text lane checks passed",
    "checks": checks,
}))
PYEOF
