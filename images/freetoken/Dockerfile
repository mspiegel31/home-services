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
ARG CUDA_TAG=13.0.1-devel-ubuntu24.04
FROM nvidia/cuda:${CUDA_TAG}

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/ft/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/local/bin/python3

RUN python3 -m venv /opt/ft \
    && /opt/ft/bin/pip install --no-cache-dir -U pip uv \
    && /opt/ft/bin/uv pip install --python /opt/ft/bin/python "freetoken[accel]" \
    && /opt/ft/bin/ft --version

ENTRYPOINT ["ft"]
CMD ["--help"]
