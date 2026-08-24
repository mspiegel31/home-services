#!/usr/bin/env bash
set -euo pipefail

# install.sh — install llama-swap as a host systemd service.
#
# Downloads the llama-swap release binary, optionally builds vllm-wrapper
# from source (if Go is installed), creates the env file, installs the
# systemd unit, and enables the service.
#
# Usage:
#   sudo ./install.sh [LLAMA_SWAP_VERSION]
#   sudo LS_VERSION=v250 ./install.sh
#
# After running:
#   1. Edit /etc/llama-swap/env with your API key and HF token
#   2. Deploy the git-sync stack in Portainer (docker-compose.yml)
#   3. systemctl start llama-swap

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LS_VERSION="${1:-${LS_VERSION:-latest}}"
INSTALL_PREFIX="${INSTALL_PREFIX:-/usr/local}"
CONFIG_DIR="/etc/llama-swap"
GIT_SYNC_DIR="/home/cloud/llama-swap"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64)  ARCH="amd64" ;;
  aarch64) ARCH="arm64" ;;
  *) echo "FATAL: unsupported arch $ARCH" >&2; exit 1 ;;
esac

echo "=== llama-swap host installer (version: $LS_VERSION, arch: $ARCH) ==="

# --- prerequisites -----------------------------------------------------------
command -v curl >/dev/null || { echo "FATAL: curl not found" >&2; exit 1; }
command -v docker >/dev/null || { echo "FATAL: docker not found" >&2; exit 1; }

# --- resolve version ---------------------------------------------------------
if [ "$LS_VERSION" = "latest" ]; then
  echo "=== Resolving latest release ==="
  LS_VERSION=$(curl -fsSL "https://api.github.com/repos/mostlygeek/llama-swap/releases/latest" \
    | grep '"tag_name"' | head -1 | cut -d'"' -f4)
  [ -z "$LS_VERSION" ] && { echo "FATAL: could not determine latest release" >&2; exit 1; }
  echo "Latest release: $LS_VERSION"
fi

# v250 → 250 (strip leading 'v' for the tarball filename)
LS_VER_NUM="${LS_VERSION#v}"

# --- download + verify llama-swap binary -------------------------------------
TARBALL="llama-swap_${LS_VER_NUM}_linux_${ARCH}.tar.gz"
URL="https://github.com/mostlygeek/llama-swap/releases/download/${LS_VERSION}/${TARBALL}"
CHECKSUMS_URL="https://github.com/mostlygeek/llama-swap/releases/download/${LS_VERSION}/llama-swap_${LS_VER_NUM}_checksums.txt"

echo "=== Downloading $URL ==="
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
curl -fsSL -o "$TMPDIR/$TARBALL" "$URL"

echo "=== Verifying checksum ==="
curl -fsSL -o "$TMPDIR/checksums.txt" "$CHECKSUMS_URL" || echo "WARN: checksums file not found, skipping verification"
if [ -f "$TMPDIR/checksums.txt" ]; then
  grep "$TARBALL" "$TMPDIR/checksums.txt" > "$TMPDIR/verify.txt"
  (cd "$TMPDIR" && sha256sum -c verify.txt)
fi

tar -xzf "$TMPDIR/$TARBALL" -C "$TMPDIR"
install -m 0755 "$TMPDIR/llama-swap" "${INSTALL_PREFIX}/bin/llama-swap"
echo "Installed: ${INSTALL_PREFIX}/bin/llama-swap"

# --- optionally build vllm-wrapper -------------------------------------------
if command -v go >/dev/null 2>&1; then
  echo "=== Building vllm-wrapper from source (${LS_VERSION}) ==="
  GOPATH_TMP=$(mktemp -d)
  trap 'rm -rf "$TMPDIR" "$GOPATH_TMP"' EXIT
  git clone --depth=1 --branch "$LS_VERSION" https://github.com/mostlygeek/llama-swap.git "$GOPATH_TMP/src"
  (cd "$GOPATH_TMP/src" && CGO_ENABLED=0 go build -trimpath -o "$TMPDIR/vllm-wrapper" ./cmd/vllm-wrapper)
  rm -rf "$GOPATH_TMP"
  install -m 0755 "$TMPDIR/vllm-wrapper" "${INSTALL_PREFIX}/bin/vllm-wrapper"
  echo "Installed: ${INSTALL_PREFIX}/bin/vllm-wrapper"
else
  echo "WARN: Go not found — skipping vllm-wrapper (sleep/wake support)."
  echo "      Install Go and re-run to enable sleep/wake."
fi

# --- env file ----------------------------------------------------------------
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/env" ]; then
  install -m 0600 "$SCRIPT_DIR/env.example" "$CONFIG_DIR/env"
  echo "Installed: $CONFIG_DIR/env (edit with your API key and HF token)"
else
  echo "Exists:    $CONFIG_DIR/env (left unchanged)"
fi

# --- git-sync bind mount directory -------------------------------------------
mkdir -p "$GIT_SYNC_DIR"
echo "Created:   $GIT_SYNC_DIR (git-sync bind mount target)"

# --- systemd unit ------------------------------------------------------------
UNIT_DIR="/etc/systemd/system"
install -m 0644 "$SCRIPT_DIR/llama-swap.service" "$UNIT_DIR/llama-swap.service"
echo "Installed: $UNIT_DIR/llama-swap.service"

systemctl daemon-reload
systemctl enable llama-swap.service
echo ""
echo "=== Done ==="
echo "  Next steps:"
echo "    1. Edit /etc/llama-swap/env with your API key and HF token"
echo "    2. Deploy the git-sync stack in Portainer"
echo "    3. systemctl start llama-swap"
echo "  Logs: journalctl -u llama-swap -f"
echo "  UI:   http://localhost:11437/ui"
