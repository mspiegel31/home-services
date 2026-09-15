FROM nousresearch/hermes-agent:v2026.9.7@sha256:63bfb6d732f49a55d453e801057273785cc61e0f6ee43db3fa2f2a79846301b7

ARG MEALIE_MCP_REVISION=02183a84b92ba88e69fa11ded8b8235cc01771eb
ARG BABYBUDDY_MCP_REVISION=9f32d446241c323602b23160d05e926161184d9f

USER root
# MCP venvs must use the world-readable system Python, not a uv-managed
# interpreter under /root (0700): the gateway drops to the hermes user, which
# cannot execute a symlink target it cannot traverse.
RUN git init /opt/mealie-mcp \
    && git -C /opt/mealie-mcp remote add origin https://github.com/rldiao/mealie-mcp-server.git \
    && git -C /opt/mealie-mcp fetch --depth 1 origin "${MEALIE_MCP_REVISION}" \
    && git -C /opt/mealie-mcp checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/mealie-mcp rev-parse HEAD)" = "${MEALIE_MCP_REVISION}" \
    && uv sync --project /opt/mealie-mcp --frozen --no-dev --no-editable --python /usr/bin/python3.13 \
    && rm -rf /opt/mealie-mcp/.git \
    && git init /opt/babybuddy-mcp \
    && git -C /opt/babybuddy-mcp remote add origin https://github.com/babybuddy/babybuddy-mcp.git \
    && git -C /opt/babybuddy-mcp fetch --depth 1 origin "${BABYBUDDY_MCP_REVISION}" \
    && git -C /opt/babybuddy-mcp checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/babybuddy-mcp rev-parse HEAD)" = "${BABYBUDDY_MCP_REVISION}" \
    && uv sync --project /opt/babybuddy-mcp --frozen --no-dev --no-editable --python /usr/bin/python3.13 \
    && rm -rf /opt/babybuddy-mcp/.git


COPY --chmod=0755 00-home-butler-seed /etc/cont-init.d/00-home-butler-seed
COPY --chmod=0755 03-managed-config /etc/cont-init.d/03-managed-config
COPY --chmod=0755 config-apply.py /usr/local/bin/hermes-config-apply
COPY --chmod=0644 config.yaml /opt/hermes-seed/config.yaml
COPY --chmod=0644 AGENTS.md /opt/hermes-seed/AGENTS.md
COPY --chmod=0644 mcp/ /opt/home-butler-mcp/

RUN /opt/mealie-mcp/.venv/bin/python -m unittest discover \
      --start-directory /opt/home-butler-mcp --pattern 'test_*.py' \
    && chown -R root:root /opt/mealie-mcp /opt/babybuddy-mcp /opt/home-butler-mcp /opt/hermes-seed \
    && chmod -R a-w /opt/mealie-mcp /opt/babybuddy-mcp /opt/home-butler-mcp /opt/hermes-seed \
    && find /opt/mealie-mcp/.venv/bin /opt/babybuddy-mcp/.venv/bin -type d -exec chmod a+x {} + \
    && find /opt/mealie-mcp/.venv/bin /opt/babybuddy-mcp/.venv/bin \( -type f -o -type l \) -exec chmod a+x {} +
