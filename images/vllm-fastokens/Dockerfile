FROM vllm/vllm-openai:v0.28.0@sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14
RUN pip install --no-cache-dir 'fastokens>=0.2.0,<0.3'

# froggeric/Qwen-Fixed-Chat-Templates v22.5, snapshot 855bffc49448e299789730ff92c9b8d834d6cc14
COPY qwen3.8-froggeric-v22.5.jinja /opt/chat-templates/qwen3.8-froggeric-v22.5.jinja
