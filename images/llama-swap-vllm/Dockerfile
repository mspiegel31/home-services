# llama-swap vLLM router: llama-swap + vllm-wrapper + Docker CLI.
# No CUDA, no model weights, no vLLM — those live in per-model backend containers.

# Build vllm-wrapper from llama-swap source (cross-compiled, CGO disabled)
FROM --platform=$BUILDPLATFORM golang:1.26-alpine AS build-wrapper
ARG TARGETOS
ARG TARGETARCH
WORKDIR /src
RUN git clone --depth=1 --branch v250 https://github.com/llama-swap/llama-swap.git .
ENV CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH
RUN go build -ldflags="-s -w" -o /out/vllm-wrapper ./cmd/vllm-wrapper

# Download pre-built llama-swap binary from the v250 release
FROM alpine:3.21 AS download
ARG TARGETARCH
RUN apk add --no-cache curl
RUN set -eux; \
    curl -fsSL -o /tmp/llama-swap.tar.gz \
      "https://github.com/llama-swap/llama-swap/releases/download/v250/llama-swap_250_linux_${TARGETARCH}.tar.gz"; \
    curl -fsSL -o /tmp/checksums.txt \
      "https://github.com/llama-swap/llama-swap/releases/download/v250/llama-swap_250_checksums.txt"; \
    grep "llama-swap_250_linux_${TARGETARCH}.tar.gz" /tmp/checksums.txt > /tmp/verify.txt; \
    cd /tmp && sha256sum -c verify.txt --strict; \
    tar -xzf llama-swap.tar.gz -C /tmp

# Runtime: Docker CLI as the multi-arch base
FROM docker:29-cli@sha256:000bb62ff495f986c9f5578eb67cc2cb98b91138eda81d7762d5371eb8a497fe
RUN apk add --no-cache ca-certificates curl
COPY --from=download /tmp/llama-swap /usr/local/bin/llama-swap
COPY --from=build-wrapper /out/vllm-wrapper /usr/local/bin/vllm-wrapper
ENTRYPOINT []
RUN llama-swap --version && vllm-wrapper --help > /dev/null && docker --version
ENTRYPOINT ["llama-swap"]
