# FreeToken MoE serving engine (https://github.com/FlashML-org/FreeToken).
#
# Serves frontier MoE checkpoints (DeepSeek-V4-Flash, Qwen MoE, GLM-5.x, ...)
# with an OpenAI/Anthropic-compatible API on :1919. llama-swap spawns this
# container lazily the same way it spawns the vLLM backend containers —
# see services/llama-swap-vllm/config.yaml.
#
# linux/amd64 only: the PyPI wheels are manylinux x86_64 and JIT kernel
# compilation needs nvcc (CUDA 13). The shared build pipeline builds both
# platforms in one buildx build, so the arm64 target builds a valid stub
# that fails fast at runtime — without it the amd64 push would fail too.
ARG CUDA_TAG=13.0.1-devel-ubuntu24.04
FROM --platform=$TARGETPLATFORM nvidia/cuda:${CUDA_TAG}

ARG TARGETPLATFORM

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/ft/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/local/bin/python3

RUN if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        python3 -m venv /opt/ft \
        && /opt/ft/bin/pip install --no-cache-dir -U pip uv \
        && /opt/ft/bin/uv pip install --python /opt/ft/bin/python "freetoken[accel]" \
        && /opt/ft/bin/ft --version; \
    else \
        echo "freetoken is only available for linux/amd64"; \
    fi

ENTRYPOINT ["ft"]
CMD ["--help"]
