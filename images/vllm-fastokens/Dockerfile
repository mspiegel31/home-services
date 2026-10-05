FROM vllm/vllm-openai:v0.31.0@sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3
RUN pip install --no-cache-dir 'fastokens>=0.2.0,<0.3'

# froggeric/Qwen-Fixed-Chat-Templates v22.5, snapshot 855bffc49448e299789730ff92c9b8d834d6cc14
COPY qwen3.8-froggeric-v22.5.jinja /opt/chat-templates/qwen3.8-froggeric-v22.5.jinja
