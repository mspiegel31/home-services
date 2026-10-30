FROM vllm/vllm-openai:v0.32.0@sha256:befccf0e7e4089aa23926bb6f887a85c0d46c2a99e6de5c5ffdf5cb7957c5b34
RUN pip install --no-cache-dir 'fastokens>=0.2.0,<0.3'

# froggeric/Qwen-Fixed-Chat-Templates v22.5, snapshot 855bffc49448e299789730ff92c9b8d834d6cc14
COPY qwen3.8-froggeric-v22.5.jinja /opt/chat-templates/qwen3.8-froggeric-v22.5.jinja
