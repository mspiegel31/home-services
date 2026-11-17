FROM vllm/vllm-openai:v0.34.0@sha256:20fdb089454afbb324efa4110a2c025ff7b27cc1a086e07aa580b18df8ad1ce1
# vLLM 0.34.0 requires fastokens >= 0.3.5 for VLLM_USE_FASTOKENS (vllm #65679).
RUN pip install --no-cache-dir 'fastokens>=0.3.5,<0.4'

# froggeric/Qwen-Fixed-Chat-Templates v22.5, snapshot 855bffc49448e299789730ff92c9b8d834d6cc14
COPY qwen3.8-froggeric-v22.5.jinja /opt/chat-templates/qwen3.8-froggeric-v22.5.jinja
