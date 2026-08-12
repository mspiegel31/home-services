# Caddy 2 with github.com/mholt/caddy-ratelimit for agent-facing rate limiting.
# The official caddy:2-alpine image does not include the rate_limit module.
# Builder runs on the BUILD platform (native amd64) and Go cross-compiles to
# the TARGET platform. Caddy builds with CGO disabled, so this is a pure-Go
# cross-compile — no QEMU emulation of the go toolchain (which is what made
# the arm64 leg take 20+ minutes / appear hung).
FROM --platform=$BUILDPLATFORM caddy:2-builder AS builder

ARG TARGETOS TARGETARCH

RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    GOOS=${TARGETOS} GOARCH=${TARGETARCH} xcaddy build \
    --with github.com/mholt/caddy-ratelimit

FROM caddy:2-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
