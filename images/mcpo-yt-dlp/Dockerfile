# Custom mcpo image with yt-dlp + ffmpeg for yt-dlp-mcp tool support.
# Base image already ships Python 3.12, uv, Node.js 22, npm, git, and mcpo.
# This layer adds the system dependencies that yt-dlp-mcp shells out to.
FROM ghcr.io/open-webui/mcpo:main

# ffmpeg: required by yt-dlp for merging separate audio/video streams
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp + curl-cffi: the binary that yt-dlp-mcp invokes for
# downloads, transcripts, and metadata extraction. Installed into the base
# image's venv at /app/.venv (VIRTUAL_ENV is already set in the base).
# curl-cffi enables yt-dlp's TLS impersonation ("impersonate target");
# without it YouTube 429s subtitle downloads from this network (2026-10-12).
# yt-dlp is pinned so YouTube extractor fixes arrive as reviewable bumps,
# not as whatever PyPI served on the day of an unrelated rebuild.
RUN uv pip install yt-dlp==2026.10.26 curl-cffi

# yt-dlp-mcp built from the `home` branch of homebernetes/yt-dlp-mcp, a fork
# of @kevinwatt/yt-dlp-mcp 0.10.2 carrying:
# - timestamped transcripts (`timestamps: true`) and `offset` pagination for
#   the caption tools, plus YTDLP_MAX_TRANSCRIPT_LENGTH / YTDLP_CHARACTER_LIMIT
#   (upstream PR kevinwatt/yt-dlp-mcp#34); upstream truncates subtitles at
#   25,000 characters with no way to fetch the rest (~3 min of auto VTT);
# - fork-only: `<lang>-orig` before `<lang>` (yt-dlp maps a bare 'en' to a
#   machine translation that YouTube 429s, 2026-10-29) and no --write-subs in
#   transcripts (YouTube 429s the manual-subtitle endpoint, 2026-10-12);
# - fork-only: hidden like counts no longer 500 the metadata summary (yt-dlp
#   reports like_count: null, not a missing key; 2026-11-25).
# Pinned to a commit; once #34 ships, return to the npm release and keep only
# the fork-only commits.
ARG YT_DLP_MCP_REPO=https://github.com/homebernetes/yt-dlp-mcp.git
ARG YT_DLP_MCP_COMMIT=f00f3a3fe268338f0a7cd97bb3858b614c548cf2
RUN git init -q /tmp/yt-dlp-mcp \
    && cd /tmp/yt-dlp-mcp \
    && git fetch -q --depth 1 "$YT_DLP_MCP_REPO" "$YT_DLP_MCP_COMMIT" \
    && git checkout -q FETCH_HEAD \
    && npm ci --no-audit --no-fund \
    && npm pack --silent \
    && npm install -g --no-audit --no-fund ./kevinwatt-yt-dlp-mcp-*.tgz \
    && cd / && rm -rf /tmp/yt-dlp-mcp

# yt-dlp-mcp validates that its downloads directory exists at startup
RUN mkdir -p /root/Downloads

# Verify all dependencies are reachable
RUN yt-dlp --version && ffmpeg -version | head -1
