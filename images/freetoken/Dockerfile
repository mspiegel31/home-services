# FreeToken MoE serving engine (https://github.com/FlashML-org/FreeToken).
#
# Serves frontier MoE checkpoints (DeepSeek-V4-Flash, Qwen MoE, GLM-5.x, ...)
# with an OpenAI/Anthropic-compatible API on :1919. llama-swap spawns this
# container lazily the same way it spawns the vLLM backend containers —
# see services/llama-swap-vllm/config.yaml.
#
# linux/amd64 only: the PyPI wheels are manylinux x86_64 and JIT kernel
# compilation needs nvcc (CUDA 13). build-images.yml pins this image to
# amd64 in the per-image policy.
ARG CUDA_TAG=13.0.1-devel-ubuntu24.04@sha256:7d2f6a8c2071d911524f95061a0db363e24d27aa51ec831fcccf9e76eb72bc92
FROM nvidia/cuda:${CUDA_TAG}

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/ft/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/local/bin/python3

RUN python3 -m venv /opt/ft \
    && /opt/ft/bin/pip install --no-cache-dir -U pip uv \
    && /opt/ft/bin/uv pip install --python /opt/ft/bin/python "freetoken[accel]==0.2.0" \
    && /opt/ft/bin/ft --version

RUN /opt/ft/bin/ft serve --help

# Triton compiles its Python CUDA driver on the serving node, not at --help.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12-dev patch \
    && rm -rf /var/lib/apt/lists/*

# kubeswap probes only HTTP status; upstream's loading-health 200 races requests.
COPY health-readiness.patch /tmp/freetoken-health-readiness.patch
RUN patch --fuzz=0 --strip=1 --directory=/opt/ft/lib/python3.12/site-packages \
    --input=/tmp/freetoken-health-readiness.patch \
    && rm /tmp/freetoken-health-readiness.patch

COPY image-smoke.py /tmp/freetoken-image-smoke.py
RUN /opt/ft/bin/python /tmp/freetoken-image-smoke.py \
    && rm /tmp/freetoken-image-smoke.py

ENTRYPOINT ["ft"]
CMD ["--help"]
