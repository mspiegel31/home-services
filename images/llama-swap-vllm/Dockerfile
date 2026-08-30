FROM ghcr.io/mostlygeek/llama-swap:unified-cuda
COPY vllm_sleep_controller.py /usr/local/bin/
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io python3 \
 && rm -rf /var/lib/apt/lists/*
