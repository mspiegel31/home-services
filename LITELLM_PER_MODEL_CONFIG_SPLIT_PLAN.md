# LiteLLM: split config.yaml into per-model files (llama-swap pattern)

## Context

`services/litellm/config.yaml` currently holds all 10 deployments (9 chat models + 1 embedding model) in one `model_list`, using YAML anchors (`&qwen38_model_info`, `&flash_next_model_info`, `<<:` merge keys) to share `model_info` blocks. The llama-swap stack was just refactored to one model per file in `services/llama-swap-vllm/models/` via its `--config-dir` flag, which the user prefers. This plan applies the same shape to LiteLLM.

LiteLLM supports this natively with the `include` directive (no build step, no custom code). Verified facts (litellm 1.103.0, installed in a throwaway venv and exercised end-to-end through `ProxyConfig._process_includes`):

- Root config declares `include: [<paths>]`; each listed file must be a YAML mapping; `model_list` lists are concatenated (root entries first, then included files in listed order), other top-level keys merge with included values winning.
- Paths resolve relative to the file that declares them (a root-config path like `models/x.yaml` resolves next to the root config). No glob support — every file is listed explicitly.
- The `include` key is stripped from the merged config. Cycles and duplicate pulls are safe.
- **No cross-file YAML anchors**: each file is parsed separately, so the current `&`/`*`/`<<:` pattern is incompatible. Shared `model_info` is fully expanded in each file.
- Missing included file → `FileNotFoundError` at startup; non-mapping file → `ValueError`.

End state: `services/litellm/models/<model-id>.yaml`, one deployment per file, each file self-contained; `config.yaml` keeps the include list, the nomic embedding entry, and all global settings. Client-visible model names, `model_info` values, routing, and the thinking callback are unchanged.

## Approach

Order matters only for the final verification: steps 1–4 are one atomic commit (config must not ship in a state where `include` points at missing files).

### 1. Create `services/litellm/models/` with 9 files

Create `services/litellm/models/`, one file per chat model, named exactly `<model-id>.yaml` (mirroring the llama-swap convention; IDs from the current `model_list`):

`qwen3.8-27b-fp8.yaml`, `qwen3.8-27b-bf16.yaml`, `qwen3.8-27b-bf16-sglang.yaml`, `qwen3.8-27b-nvfp4.yaml`, `qwen3.8-flash-next-nvfp4.yaml`, `swift-1.5-flash-nvfp4.yaml`, `swift-1.5-nvfp4.yaml`, `swift-1.5-bf16.yaml`, `swift-1.5-awq.yaml`

Each file has exactly this shape — the current entry moved verbatim, with its anchor references expanded:

```yaml
# <model-id> — one deployment in the litellm config split.
# Global settings (master_key, redis, cache, callbacks) live in ../config.yaml.
# This file defines exactly one top-level key: model_list, with one entry.

model_list:
  - model_name: <model-id>
    litellm_params:
      model: <model-id>
      api_base: http://192.168.1.98:11437/v1
      api_key: os.environ/LLAMA_SWAP_API_KEY
      custom_llm_provider: <hosted_vllm|openai>
    model_info:
      <expanded block>
```

Per-file specifics (everything else identical to the entry at `services/litellm/config.yaml:41-214`):

- `qwen3.8-27b-fp8.yaml`: `custom_llm_provider: hosted_vllm`. `model_info` = the current `&qwen38_model_info` block (lines 47-71) verbatim, including its comments, with the anchor `&qwen38_model_info` removed.
- `qwen3.8-27b-bf16.yaml`: `hosted_vllm`; expanded `&qwen38_model_info` **plus** `max_output_tokens: 262144` (currently line 81).
- `qwen3.8-27b-bf16-sglang.yaml`: **`custom_llm_provider: openai`** (only entry that differs; currently line 88); expanded `&qwen38_model_info` plus `max_output_tokens: 262144`.
- `qwen3.8-27b-nvfp4.yaml`: `hosted_vllm`; expanded `&qwen38_model_info`.
- `qwen3.8-flash-next-nvfp4.yaml`: `hosted_vllm`; `model_info` = the current `&flash_next_model_info` block (lines 108-125) verbatim (it already fully re-lists `supported_openai_params`; keep it), anchor removed.
- `swift-1.5-flash-nvfp4.yaml`: `hosted_vllm`; expanded `&flash_next_model_info` **plus** `max_output_tokens: 262144` and its comment (lines 136-141).
- `swift-1.5-nvfp4.yaml`: `hosted_vllm`; expanded `&qwen38_model_info` **plus** `reasoning_effort: [low, medium, xhigh]`, `max_output_tokens: 262144`, `supports_function_calling: true`, `supports_tool_choice: true`, and the full 10-item `supported_openai_params` list (lines 150-166).
- `swift-1.5-bf16.yaml`, `swift-1.5-awq.yaml`: identical shape to `swift-1.5-nvfp4.yaml` (lines 168-190 and 192-214 respectively).

Keep each entry's existing inline comments with it. Do **not** re-introduce anchors or `<<:` anywhere — the whole point is self-contained files.

### 2. Rewrite `services/litellm/config.yaml`

Replace the 9 chat-model entries (lines 38-214, including the anchor-intro comment at 38-39) with:

```yaml
# Chat-model deployments live in ./models/*.yaml — one model per file, pulled
# in via LiteLLM's `include` directive (no glob; every file is listed).
# Merge semantics: model_list entries are concatenated in listed order;
# a model id must appear in exactly one file.
# To add a model, drop a new <model-id>.yaml in models/ and add it to the
# include list below.
include:
  - models/qwen3.8-27b-fp8.yaml
  - models/qwen3.8-27b-bf16.yaml
  - models/qwen3.8-27b-bf16-sglang.yaml
  - models/qwen3.8-27b-nvfp4.yaml
  - models/qwen3.8-flash-next-nvfp4.yaml
  - models/swift-1.5-flash-nvfp4.yaml
  - models/swift-1.5-nvfp4.yaml
  - models/swift-1.5-bf16.yaml
  - models/swift-1.5-awq.yaml

model_list:
  - model_name: nomic-embed-text-v2-moe
    ...
```

- Keep the `nomic-embed-text-v2-moe` entry (lines 22-36) in the root file unchanged — it is the only deployment that does not route through llama-swap.
- Keep `general_settings` (216-224) and `litellm_settings` (225-235) byte-identical.
- Update the header comment lines 16-18 ("change the value on every model_list entry") to note that `api_base`/`api_key` now live in `models/*.yaml`.
- The nomic entry's placement first in the merged list is preserved automatically (root entries merge before included ones).

### 3. Tighten the git-sync healthcheck

In `services/litellm/docker-compose.yml`, change the git-sync healthcheck (line 73) to also require the model files, matching the llama-swap pattern (`services/llama-swap-vllm/docker-compose.yml:68`):

```yaml
test: ["CMD-SHELL", "test -f /git/current/services/litellm/config.yaml && ls /git/current/services/litellm/models/*.yaml >/dev/null && curl -fsS http://127.0.0.1:1234/"]
```

No sparse-checkout change needed: the checkout spec (lines 32-37) already includes the whole `services/litellm/` tree, so `models/` syncs automatically.

### 4. Update `services/litellm/AGENTS.md`

In the "Config management" section, add one line under the config-source list: chat-model deployments live in `models/<model-id>.yaml` via the `include` directive in `config.yaml` (explicit file list, no glob; `model_list` concatenates in listed order). Note that LiteLLM `include` files are parsed separately, so YAML anchors/merge keys do not cross file boundaries — model files are fully self-contained.

### 5. Smoke test (pre-deploy, on this machine)

Run a throwaway verification that the merged config is byte-equivalent to today's in everything that matters:

```bash
python3 -m venv /tmp/litellm-split-check
/tmp/litellm-split-check/bin/pip install -q "litellm[proxy]"
```

Then a throwaway script (do not commit it) that:
1. Copies `services/litellm/config.yaml` + `services/litellm/models/` to a temp dir.
2. Loads the root file with `ProxyConfig()._load_yaml_file` and merges via `await pc._process_includes(config=cfg, config_file_path=<abs root path>)`.
3. Asserts:
   - `"include"` not in the merged config.
   - Merged `model_list` has exactly 10 entries; names in order: `nomic-embed-text-v2-moe`, then the 9 chat IDs in include-list order.
   - Each of the 9 chat entries equals the corresponding *current* (pre-refactor) entry from the committed `config.yaml` — compare the full `litellm_params` and `model_info` dicts (this catches any expansion typo of the anchor blocks).
   - `general_settings` and `litellm_settings` unchanged (compare to current file's values).
   - `qwen3.8-27b-bf16-sglang` specifically has `custom_llm_provider == "openai"`, all others `hosted_vllm`.
4. Fails loudly on any mismatch; print `PASS` on success.

Also run the existing callback suite (unaffected, but cheap): `python3 services/litellm/test_custom_callbacks.py` → existing pass output.

### 6. Deploy + live verification

Commit and push `main` (Portainer polls every 5 min and redeploys the stack). Then verify against the running proxy (master key from Portainer; LAN path `http://192.168.1.98:4000`):

1. `curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://192.168.1.98:4000/v1/models` → exactly the same 10 model names as before.
2. `curl ... /v2/model/info` → spot-check `swift-1.5-nvfp4` and `qwen3.8-27b-bf16-sglang`: `context_window: 262144`, `reasoning_effort: [low, medium, xhigh]` (swift), `max_output_tokens: 262144` (bf16-sglang) all present — proves the expanded anchor blocks survived the split.
3. Chat smoke through llama-swap: `POST /chat/completions` with `model: swift-1.5-nvfp4`, `max_tokens: 16`, a trivial prompt → 200 with a completion (proves routing + thinking callback intact; the model wakes on demand, so allow up to the usual llama-swap load time).
4. `docker logs litellm` (on the inference host) → startup line `Set models:` lists all 10; no `FileNotFoundError`/`ValidationError` from include processing.

## Critical files & anchors

- `services/litellm/config.yaml:38-214` — the 9 chat entries being extracted; anchors `&qwen38_model_info` (line 47) and `&flash_next_model_info` (line 108) define the two expanded blocks.
- `services/litellm/docker-compose.yml:73` — git-sync healthcheck; pattern to copy at `services/llama-swap-vllm/docker-compose.yml:68`.
- `services/llama-swap-vllm/models/swift-1.5-nvfp4.yaml` — the prior art for file shape (header comment + single top-level key).
- `services/litellm/custom_callbacks.py:39-50` — `LocalReasoningModel` enum keyed by model ID; untouched, but the reason model IDs must stay byte-identical.

## Assumptions & contingencies

- **Duplicated `model_info` is acceptable.** LiteLLM `include` files are parsed independently, so the shared Qwen3.8/Swift `model_info` (~25 lines) is repeated across 8 files rather than anchored. Chosen over a build/concat step: zero moving parts, matches how the llama-swap split already trades DRY for per-file locality.
- **`main-stable` image is new enough.** `include` requires litellm ≥ ~v1.74 (Nov 2024); the deployed `main-stable` tag is current (1.103.0 verified in venv). If startup ever logs a missing-file or unknown-key error after a future image pin, check the image's bundled version first.
- **If the live `/v1/models` check shows a duplicate name** (e.g., a model added via Admin UI/DB under the same name — `store_model_in_db` is on, so DB models coexist with YAML ones): that pre-dates this change; resolve in the Admin UI, not in these files.
- **If a future model is added via Admin UI only**, it is unaffected: DB models are served alongside YAML models and never replaced by them.
