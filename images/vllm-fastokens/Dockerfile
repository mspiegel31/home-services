FROM vllm/vllm-openai:v0.29.0@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1
RUN pip install --no-cache-dir 'fastokens>=0.2.0,<0.3'

# froggeric/Qwen-Fixed-Chat-Templates v22.5, snapshot 855bffc49448e299789730ff92c9b8d834d6cc14
COPY qwen3.8-froggeric-v22.5.jinja /opt/chat-templates/qwen3.8-froggeric-v22.5.jinja
