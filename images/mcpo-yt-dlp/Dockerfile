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
# yt-dlp is pinned so YouTube extractor fixes arrive as reviewable bumps,
# not as whatever PyPI served on the day of an unrelated rebuild.
RUN uv pip install yt-dlp==2026.10.26 curl-cffi

# yt-dlp-mcp pinned + patched (subtitle-orig-captions.patch):
# - drops --write-subs from transcripts: YouTube 429s the manual-subtitle
#   endpoint from this network and yt-dlp aborts the whole call (2026-10-12);
# - requests `<lang>-orig` before `<lang>`: on videos with several ASR tracks
#   yt-dlp maps a bare 'en' to a machine translation (timedtext tlang=), which
#   YouTube 429s far harder than the original track (2026-10-29).
# Pinned so `git apply` fails the build instead of drifting on an upgrade.
COPY subtitle-orig-captions.patch /tmp/
RUN npm install -g @kevinwatt/yt-dlp-mcp@0.10.0 \
    && cd "$(npm root -g)/@kevinwatt/yt-dlp-mcp" \
    && git apply /tmp/subtitle-orig-captions.patch \
    && rm /tmp/subtitle-orig-captions.patch

# yt-dlp-mcp validates that its downloads directory exists at startup
RUN mkdir -p /root/Downloads

# Verify all dependencies are reachable
RUN yt-dlp --version && ffmpeg -version | head -1
