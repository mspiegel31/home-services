# Caddy 2 with github.com/mholt/caddy-ratelimit for agent-facing rate limiting.
# The official caddy:2-alpine image does not include the rate_limit module.
FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/mholt/caddy-ratelimit

FROM caddy:2-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
