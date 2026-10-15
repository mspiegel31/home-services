FROM ghcr.io/local-inference-lab/vllm:release-10152026@sha256:745feb916ee816f5409fd58386114be4f22fbede7f9c0e0a7b8c4fe8dac0fb29

# CSF experts have zero-sized parameters during vLLM's construction-time
# offload pass. Their eventual packed allocation must honor that same budget.
COPY csf_ram_offload.py /opt/venv/lib/python3.12/site-packages/vllm/model_executor/layers/quantization/csf_ram_offload.py
COPY nvfp4-csf-ram.patch /tmp/nvfp4-csf-ram.patch
RUN patch --fuzz=0 -p1 -d /opt/venv/lib/python3.12/site-packages/vllm < /tmp/nvfp4-csf-ram.patch \
    && rm /tmp/nvfp4-csf-ram.patch
