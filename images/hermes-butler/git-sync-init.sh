#!/usr/bin/env sh
# One-shot initial managed-config sync. Runs once (restart: "no") so the gateway
# container can depend on it (condition: service_completed_successfully). On
# success the managed snapshot is on the shared volume and the boot gate has its
# input; on failure the gateway never starts, which is the desired fail-closed
# behavior — a missing snapshot means no validated policy.
set -eu

# Reuse the same sync logic as the loop, but exit after the first successful pass.
# Source the loop's functions is not possible in POSIX sh without running its main
# loop, so replicate the minimal path: clone-or-fetch + sparse-checkout + copy.
repo="${GIT_SYNC_REPO:?set GIT_SYNC_REPO in Portainer}"
branch="${GIT_SYNC_BRANCH:-main}"
subpath="${GIT_SYNC_SUBPATH:-services/hermes/managed}"
dst="${HERMES_MANAGED_DIR:?set HERMES_MANAGED_DIR}"
scratch="${HERMES_MANAGED_SCRATCH:-/opt/hermes-managed-repo}"
token="${GIT_SYNC_TOKEN:-}"

if [ -n "$token" ]; then
    encoded=$(printf '%s' "$token" | sed 's/@/%40/g; s/#/%23/g; s/:/%3A/g')
    authed="${repo/@https:/@https://oauth2:${encoded}@}"
else
    authed="$repo"
fi

if [ ! -d "$scratch/.git" ]; then
    git clone --filter=blob:none --no-checkout --branch "$branch" "$authed" "$scratch"
fi
git -C "$scratch" sparse-checkout set "$subpath"
git -C "$scratch" fetch --depth 1 origin "$branch"
git -C "$scratch" checkout --detach "origin/$branch" >/dev/null 2>&1 \
    || git -C "$scratch" reset --hard FETCH_HEAD >/dev/null 2>&1 || true

staged="$scratch/$subpath"
if [ ! -d "$staged" ]; then
    echo "[git-sync-init] managed subtree $subpath not found; REFUSING to start gateway" >&2
    exit 1
fi

mkdir -p "$dst"
for entry in "$dst"/*; do
    [ -e "$entry" ] || continue
    [ "$entry" = "$dst/.commit" ] && continue
    rm -rf "$entry"
done
cp -R "$staged/." "$dst/"
c=$(git -C "$scratch" rev-parse HEAD)
printf '%s' "$c" > "$dst/.commit"
echo "[git-sync-init] synced $subpath at $c"
