---
name: add-model
description: Wire a freshly downloaded model quant into the local inference stack — llama-swap router, LiteLLM gateway, and (for Qwen3.x) the OMP tool-call compat entries. Use whenever the user says they downloaded or pulled a model / quant / checkpoint (e.g. a new NVFP4, FP8, AWQ, bf16, or GGUF of Qwen3.x, Swift, LFM, or any other served model) and wants it "added", "wired up", "served", or "available" in OMP, or asks to expose/serve/register a model in llama-swap or litellm. Make sure to use this skill even when the user only says "add <model>" or "new model is on the box" without naming the stacks.
compatibility: home-services repo (services/llama-swap-vllm, services/litellm, .agents/skills), OMP + chezmoi dotfiles (~/dotfiles), inference-box LAN host 192.168.1.98.
---

# Add a model

Wire a new model quant into the local inference stack end-to-end so it is
served through llama-swap, exposed through the LiteLLM gateway, and (for
Qwen3.x) usable for tool calls from OMP.

The serving path is:

```
client (OMP) -> LiteLLM :4000 -> llama-swap :11437 -> vLLM backend container(s) on the inference box
```

Each layer is a separate config; the same model id must line up across all of
them, and a missing or mismatched layer fails *silently* (chat works, but the
model is absent from a router set, or OMP loses its tool/thinking controls).
Treat "the model id appears in every layer with the right shape" as the
definition of done, then verify the live endpoints.

## The layers, in order

1. **Checkpoint on the inference box** (the user does this). HF caches live
   under `/mnt/models/huggingface` on the inference box (LAN `192.168.1.98`);
   the backend bind-mounts `/mnt/models` as `/models` with
   `HF_HOME=/models/huggingface`. Confirm the HF repo / local path exists
   before writing any config.
2. **llama-swap** — a backend definition that tells the router how to spawn a
   vLLM container for the checkpoint.
3. **LiteLLM** — a deployment that points at the llama-swap router, so the
   model id is exposed to clients at `:4000`.
4. **LiteLLM thinking callback** — for any model that needs the local
   Qwen3.8/Froggeric thinking-control translation, the id must be registered.
5. **OMP tool-call compat** (Qwen3.x only) — model overrides in the OMP
   profile `models.yml` so OMP sends tool calls in a dialect the model's
   native parser understands.

Read `services/llama-swap-vllm/AGENTS.md` and `services/litellm/AGENTS.md`
first — they carry the gotchas this skill does not restate (no
`--trust-remote-code`, macros must be a mapping, `api_base` must keep `/v1`,
`custom_llm_provider` required, etc.).

---

## 1. llama-swap backend

New backends are one file each under `services/llama-swap-vllm/models/`. Copy an
existing model file in the same family as the closest template (a Qwen3.8 NVFP4
or FP8 file, not an unrelated one), then adapt it:

- **Model id** (the `models:` key and the file name): `<family>-<size/variant>-<quant>`
  with the family's dots kept (`qwen3.8-27b-nvfp4`, `swift-1.5-fp8`), matching
  what the user calls the lane. It must be unique across all `models/` files —
  a duplicate is a hard error at router load.
- **`name` / `description`**: human-readable; description should say what the
  quant is and its notable serving traits (KV dtype, spec decode on/off,
  context length).
- **`capabilities` / `metadata`**: match the checkpoint's real capabilities
  (vision in/out, tools, context). `metadata.reasoning_effort` should list the
  tiers the chat template actually supports.
- **`macros.checkpoint`**: the HF repo id (or the exact local path) that the
  backend loads. This is what must match what the user downloaded.
- **`proxy`** and **`--name`**: the vLLM container name, kept in sync between
  the two (`proxy: http://<container>:8000`, `--name <container>`). It is the
  model id with dots turned into hyphens, prefixed `vllm-` (e.g. id
  `qwen3.8-27b-nvfp4` -> container `vllm-qwen3-8-27b-nvfp4`).
- **`cmd`**: start from the closest existing `cmd` and change only what this
  checkpoint genuinely needs (KV dtype, attention backend, spec decode,
  quantization). Keep the shared macros (`${DOCKER_PREFIX}`, `${VLLM_COMMON}`,
  and `${QWEN38_COMMON}` for Qwen3.x) — they encode the vLLM flags that are
  correct for this hardware. Add a comment block explaining any non-obvious
  flag choice, the way the existing files do.
- **`cmdStop`**: `docker stop --time 90 <container>`.

**Routing.** llama-swap only proxies a model that is in a routing set. In
`services/llama-swap-vllm/config.yaml`, add the new id to the appropriate set in
the `routing:` matrix (the `co-resident` set for a standard 27B-class lane, or a
dedicated set if it should be addressable on its own). Forgetting this is the
most common silent failure: the backend loads but requests 404 at the router.

## 2. LiteLLM deployment

One file per model under `services/litellm/models/`. Copy the closest existing
deployment file and adapt:

- `model_name` and `litellm_params.model`: the same id as the llama-swap backend.
- `api_base`: `http://192.168.1.98:11437/v1` — keep the `/v1` suffix (llama-swap
  serves OpenAI only under it).
- `api_key`: `os.environ/LLAMA_SWAP_API_KEY`.
- `custom_llm_provider`: `hosted_vllm` for local chat models (this is what makes
  LiteLLM discovery route OMP to Chat Completions, where the thinking callback
  reaches it).
- `model_info`: context window, reasoning/vision flags, `reasoning_effort` tiers,
  and — for Qwen3.x with tool calling — `supports_function_calling: true` and
  `supports_tool_choice: true` (so OMP keeps native tool calls on vLLM's
  `qwen3_xml` parser instead of its in-band text fallback).

**Include it.** In `services/litellm/config.yaml`, add the new file to the
`include:` list (explicit list, no glob). A file that exists but is not listed is
silently not loaded.

## 3. LiteLLM thinking callback (Qwen3.x / local reasoning lanes)

If the model uses the Froggeric/Qwen3.8 thinking contract (i.e. it will get the
same thinking-control translation), its id must be a member of the
`LocalReasoningModel` enum in `services/litellm/custom_callbacks.py`. Add a new
member for the new id (name it in the existing `QWEN38_*` / `SWIFT_1_5_*` style).

If it belongs to a family that gets the xhigh default (currently the Swift 1.5
lanes), also add it to the `uses_froggeric_xhigh_default` tuple in
`LocalReasoningRequestAdapter._transform`.

Then add a smoke test for the new id in
`services/litellm/test_custom_callbacks.py` (mirror an existing lane's test), and
run the suite: `python3 test_custom_callbacks.py`. After a callback change the
`litellm` container must be restarted to reload the module.

If the new model is *not* a local reasoning model (no thinking controls), skip
this step.

## 4. OMP tool-call compat (Qwen3.x only)

For a Qwen3.x model, OMP needs model overrides so it:
- reports the model as supporting tools,
- sends tool calls / tool choice in the shape vLLM's `qwen3_xml` parser expects,
- and (for the thinking lanes) exposes the reasoning-effort ladder.

The live config is `~/.omp/profiles/<profile>/agent/models.yml`, but the
`modelOverrides:` block is shared across profiles via the chezmoi template
`~/dotfiles/.chezmoitemplates/omp/litellm-provider.yml.tmpl` — **add the entry
there** so every profile picks it up, not just the one that's active. The
profile `models.yml.tmpl` files render that template, so the one source of truth
is the chezmoi template.

Copy the shape of an existing Qwen3.8 lane (e.g. `qwen3.8-27b-nvfp4`):

```yaml
<new-model-id>:
  reasoning: true
  supportsTools: true
  thinking:
    mode: effort
    efforts: [low, medium, xhigh]
    requiresEffort: false
  compat:
    supportsToolChoice: true
    thinkingFormat: qwen-chat-template
    qwenTemplateReasoningEffort: true
```

(The `flash-next` lanes add `replayReasoningContent: true` and
`qwenPreserveThinking: true` — include those only if the new model is a
flash/next variant that needs reasoning replay.) The override key **must match
the id LiteLLM serves** (i.e. your `model_name`), not the HF repo id.

If the change lands in `~/dotfiles`, note that it takes effect on the next
`chezmoi apply` — don't hand-edit the rendered `~/.omp` file.

## 5. Verify

After the config is in place (and, on a live box, after the relevant
containers/Portainer stack have reloaded — both stacks git-sync `main` and
activate on a deliberate restart):

- **llama-swap**: the new id appears in the router's model list and a routing
  set includes it. A minimal chat completion through the router returns a
  generated (non-error) response.
- **LiteLLM**: the id appears at `/v1/models` and a chat completion through
  `:4000` works. For a tool-calling model, confirm OMP's discovery
  (`/v2/model/info`) shows `supports_function_calling` / `supports_tool_choice`
  and the effort ladder, so the client won't silently fall back to the text
  tool dialect.
- **OMP (Qwen3.x)**: a tool-using request against the new model produces a real
  structured tool call (not OMP's in-band text fallback) and thinking/effort
  controls are honored.

Report which layers were changed and which verifications passed. If the live
stacks can't be reached from here (no LAN access), say so explicitly and list
the exact commands to run on/against the inference box — do not claim live
verification that wasn't performed.

## Commit

Keep the change set to the layers this model actually needs. A typical Qwen3.x
NVFP4 lane touches: `services/llama-swap-vllm/models/<id>.yaml` (new),
`services/llama-swap-vllm/config.yaml` (routing), `services/litellm/models/<id>.yaml`
(new), `services/litellm/config.yaml` (include), `services/litellm/custom_callbacks.py`
+ `test_custom_callbacks.py`, and the dotfiles `litellm-provider.yml.tmpl`.
