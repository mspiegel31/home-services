# Custom mcpo image with yt-dlp + ffmpeg for yt-dlp-mcp tool support.
# Base image already ships Python 3.12, uv, Node.js 22, npm, git, and mcpo.
# This layer adds the system dependencies that yt-dlp-mcp shells out to.
FROM ghcr.io/open-webui/mcpo:main

# ffmpeg: required by yt-dlp for merging separate audio/video streams
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp: the binary that @kevinwatt/yt-dlp-mcp invokes for downloads,
# transcripts, and metadata extraction. Installed into the base image's
# venv at /app/.venv (VIRTUAL_ENV is already set in the base).
RUN uv pip install yt-dlp

# Pre-install the npm package so npx doesn't download on every container start
RUN npm install -g @kevinwatt/yt-dlp-mcp@latest

# Verify all dependencies are reachable
RUN yt-dlp --version && ffmpeg -version | head -1
