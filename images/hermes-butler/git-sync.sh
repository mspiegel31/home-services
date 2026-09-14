#!/usr/bin/env sh
# git-sync: keep $HERMES_MANAGED_DIR (a shared volume) as a fresh copy of the
# managed Hermes configuration subtree from the home-services repo, and stamp
# the resolved commit so config-apply can be version-aware.
#
# Runs a bounded pull loop so config pushed via git propagates to the container
# without a restart. Conventions (AGENTS.md): the repo is fetched over plain
# HTTPS; credentials for a private repo come from $GIT_SYNC_TOKEN (set in
# Portainer) and are injected into the remote URL, never written to disk or the
# image. The clone lives in a scratch dir; only the managed subtree is copied to
# the shared volume, so a failed clone never corrupts the applied snapshot.
set -eu

repo="${GIT_SYNC_REPO:?set GIT_SYNC_REPO in Portainer}"
branch="${GIT_SYNC_BRANCH:-main}"
subpath="${GIT_SYNC_SUBPATH:-services/hermes/managed}"
dst="${HERMES_MANAGED_DIR:?set HERMES_MANAGED_DIR}"
scratch="${HERMES_MANAGED_SCRATCH:-/opt/hermes-managed-repo}"
interval="${GIT_SYNC_INTERVAL:-30}"
token="${GIT_SYNC_TOKEN:-}"

if [ -n "$token" ]; then
    encoded=$(printf '%s' "$token" | sed 's/@/%40/g; s/#/%23/g; s/:/%3A/g')
    authed="${repo/@https:/@https://oauth2:${encoded}@}"
else
    authed="$repo"
fi

stamp() {
    c=$(git -C "$scratch" rev-parse HEAD 2>/dev/null || echo unversioned)
    printf '%s' "$c" > "$dst/.commit"
}

sync_once() {
    if [ ! -d "$scratch/.git" ]; then
        git clone --filter=blob:none --no-checkout --branch "$branch" "$authed" "$scratch"
    fi
    git -C "$scratch" sparse-checkout set "$subpath"
    git -C "$scratch" fetch --depth 1 origin "$branch"
    git -C "$scratch" checkout --detach "origin/$branch" >/dev/null 2>&1 \
        || git -C "$scratch" reset --hard FETCH_HEAD >/dev/null 2>&1 || true

    # Copy only the managed subtree to the shared volume root.
    staged="$scratch/$subpath"
    if [ ! -d "$staged" ]; then
        echo "[git-sync] managed subtree $subpath not found at commit; keeping prior snapshot" >&2
        return 1
    fi
    tmp=$(mktemp -d "$dst/.staging.XXXX")
    cp -R "$staged/." "$tmp/"
    # Atomically replace the snapshot's contents (keep the volume root stable).
    for entry in "$tmp"/* "$tmp"/.[!.]* ; do
        [ -e "$entry" ] || continue
        base=$(basename "$entry")
        if [ "$base" = ".commit" ]; then continue; fi
        if [ -d "$entry" ]; then
            rm -rf "$dst/$base"; mv "$entry" "$dst/$base"
        else
            mv "$entry" "$dst/$base"
        fi
    done
    rmdir "$tmp"
    stamp
}

echo "[git-sync] Syncing $subpath from $repo ($branch) to $dst"
sync_once
echo "[git-sync] Initial sync complete at $(cat "$dst/.commit")"

while :; do
    sleep "$interval"
    if ! sync_once; then
        echo "[git-sync] pull failed this cycle; retrying next interval" >&2
    fi
done
