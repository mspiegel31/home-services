# llama-swap-vllm

GitOps stack (Portainer CE) for the single-host llama-swap router + vLLM backends.
Secrets (`LLAMA_SWAP_API_KEY`, `HF_TOKEN`) are injected by Portainer — never commit them.

## `config.yaml` rules

- **Never add `--trust-remote-code` to a model's `cmd`.** Pin a vLLM image that
  supports the architecture natively instead of executing remote checkpoint code.
  - *Documented exception:* `ornith-ai/Ornith-1.5-35B-A3B-NVFP4` ships its vendor
    vLLM recipe with `--trust-remote-code` (arch `qwen3_5_moe`, needs Transformers
    >= 5.8.1). Keep it on Ornith until on-GPU verification proves it loads without
    the flag; then drop it and this exception.
- `macros` (global and per-model) must be a YAML **mapping** (`NAME: value`), never
  a list of `{name, value}` — llama-swap v250 rejects non-mapping blocks with
  "macros must be a mapping".
- `--enable-prefix-caching` lives in the `VLLM_COMMON` macro (all backends); do not
  duplicate it per model.
