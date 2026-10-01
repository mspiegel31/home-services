#!/bin/bash
# Deterministic checks for the Qwen3.8 NVFP4 (Hy3) lane task. Stdlib-only Python.
# Validates that one new model (id qwen3.8-27b-nvfp4-hy3) is wired consistently
# through llama-swap, litellm, the thinking callback, and the dotfiles template.
python3 - <<'PYEOF'
import json, re, subprocess, sys
from pathlib import Path

ID = "qwen3.8-27b-nvfp4-hy3"
CP = "HuggingFaceTB/Qwen3.8-27B-Hy3-NVFP4"

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
    # container name consistency across --name / proxy / cmdStop
    name = re.search(r"--name\s+(\S+)", ls)
    proxy = re.search(r"proxy:\s*http://([^/:]+):\d+", ls)
    stop = re.search(r"cmdStop:\s*docker stop --time \d+\s+(\S+)", ls)
    vals = {g.group(1) for g in (name, proxy, stop) if g}
    consistent = len(vals) == 1 and "hy3" in next(iter(vals), "")
    add("ls-container-consistent", consistent, f"--name/proxy/cmdStop = {sorted(vals)}")
    add("ls-no-trust-remote-code", "--trust-remote-code" not in ls, "must not load remote code")
    add("ls-no-spec-decode", "speculative-config" not in ls and "--speculative" not in ls, "no MTP head -> no spec decode")
    add("ls-fp32-ssm", "float32" in ls and re.search(r"mamba-ssm-cache-dtype\s+float32", ls) is not None, "GDN state in FP32")
    add("ls-froggeric-template", re.search(r"chat-template\s+\S*froggeric", ls) is not None, "Froggeric chat template")
    add("ls-qwen38-tool-macro", "${QWEN38_COMMON}" in ls or "QWEN38_COMMON" in ls, "Qwen3.x tool macro")

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
    add("lt-tool-choice", re.search(r"supports_tool_choice:\s*true", lt) is not None, "supports_tool_choice")
ltconf = read("services/litellm/config.yaml")
add("lt-include", f"models/{ID}.yaml" in ltconf, "file listed in litellm include")

# --- thinking callback -------------------------------------------------------
cb = read("services/litellm/custom_callbacks.py")
add("cb-enum-member", ID in cb, "id registered in LocalReasoningModel")
cb_test = read("services/litellm/test_custom_callbacks.py")
add("cb-test-refs-id", ID in cb_test, "smoke test exercises the new id")
try:
    r = subprocess.run([sys.executable, "test_custom_callbacks.py"], cwd="services/litellm",
                       capture_output=True, text=True, timeout=60)
    out = (r.stdout or "") + (r.stderr or "")
    # unittest writes its summary to stderr; trust the exit code and the OK line.
    suite_ok = r.returncode == 0 and "OK" in out
    add("cb-suite-passes", suite_ok, out.strip().splitlines()[-1] if out.strip() else "no output")
except Exception as e:
    add("cb-suite-passes", False, f"failed to run: {e}")

# modelOverrides keys sit at exactly 6 spaces; the block runs until the next 6-space key.
tmpl = read("dotfiles/litellm-provider.yml.tmpl")
ov = re.search(r"^      %s:\s*\n(.*?)(?=^      \S|\Z)" % re.escape(ID), tmpl, re.M | re.S)
add("dot-override-block", ov is not None, "model override under the exact id")
if ov:
    block = ov.group(1)
    add("dot-supports-tools", "supportsTools: true" in block, "supportsTools")
    add("dot-tool-choice", "supportsToolChoice: true" in block, "compat.supportsToolChoice")
    add("dot-qwen-template", "thinkingFormat: qwen-chat-template" in block, "qwen-chat-template compat")

passed = sum(c["passed"] for c in checks)
print(json.dumps({
    "score": passed / len(checks),
    "details": f"{passed}/{len(checks)} qwen3.8-nvfp4-hy3 lane checks passed",
    "checks": checks,
}))
PYEOF
