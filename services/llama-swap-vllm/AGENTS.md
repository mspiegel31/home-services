# llama-swap-vllm

GitOps stack (Portainer CE) for the single-host llama-swap router + vLLM backends.
Secrets (`LLAMA_SWAP_API_KEY`, `HF_TOKEN`) are injected by Portainer — never commit them.

## `config.yaml` rules

- **Never add `--trust-remote-code` to a model's `cmd`.** Every backend must load
  without executing Python code from its model repository.
- `macros` (global and per-model) must be a YAML **mapping** (`NAME: value`), never
  a list of `{name, value}` — llama-swap v250 rejects non-mapping blocks with
  "macros must be a mapping".
- `--enable-prefix-caching` lives in the `VLLM_COMMON` macro (all backends); do not
  duplicate it per model.
