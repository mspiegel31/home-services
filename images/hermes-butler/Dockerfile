FROM nousresearch/hermes-agent:v2026.9.7@sha256:63bfb6d732f49a55d453e801057273785cc61e0f6ee43db3fa2f2a79846301b7

ARG MEALIE_MCP_REVISION=02183a84b92ba88e69fa11ded8b8235cc01771eb

USER root
RUN git init /opt/mealie-mcp \
    && git -C /opt/mealie-mcp remote add origin https://github.com/rldiao/mealie-mcp-server.git \
    && git -C /opt/mealie-mcp fetch --depth 1 origin "${MEALIE_MCP_REVISION}" \
    && git -C /opt/mealie-mcp checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/mealie-mcp rev-parse HEAD)" = "${MEALIE_MCP_REVISION}" \
    && uv sync --project /opt/mealie-mcp --frozen --no-dev --no-editable \
    && rm -rf /opt/mealie-mcp/.git

COPY --chmod=0755 00-home-butler-seed /etc/cont-init.d/00-home-butler-seed
COPY --chmod=0644 config.yaml /opt/hermes-seed/config.yaml
COPY --chmod=0644 AGENTS.md /opt/hermes-seed/AGENTS.md
COPY --chmod=0644 mcp/ /opt/home-butler-mcp/

RUN /opt/mealie-mcp/.venv/bin/python -m unittest discover \
      --start-directory /opt/home-butler-mcp --pattern 'test_*.py' \
    && chown -R root:root /opt/mealie-mcp /opt/home-butler-mcp /opt/hermes-seed \
    && chmod -R a-w /opt/mealie-mcp /opt/home-butler-mcp /opt/hermes-seed
