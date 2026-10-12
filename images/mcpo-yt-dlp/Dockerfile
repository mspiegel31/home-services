# Custom mcpo image with yt-dlp + ffmpeg for yt-dlp-mcp tool support.
# Base image already ships Python 3.12, uv, Node.js 22, npm, git, and mcpo.
# This layer adds the system dependencies that yt-dlp-mcp shells out to.
FROM ghcr.io/open-webui/mcpo:main

# ffmpeg: required by yt-dlp for merging separate audio/video streams
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp + curl-cffi: the binary that @kevinwatt/yt-dlp-mcp invokes for
# downloads, transcripts, and metadata extraction. Installed into the base
# image's venv at /app/.venv (VIRTUAL_ENV is already set in the base).
# curl-cffi enables yt-dlp's TLS impersonation ("impersonate target");
# without it YouTube 429s subtitle downloads from this network (2026-10-12).
RUN uv pip install yt-dlp curl-cffi

# yt-dlp-mcp validates that its downloads directory exists at startup
RUN mkdir -p /root/Downloads

# Verify all dependencies are reachable
RUN yt-dlp --version && ffmpeg -version | head -1
