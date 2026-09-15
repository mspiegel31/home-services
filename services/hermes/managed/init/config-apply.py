#!/usr/bin/env python3
"""Apply the managed Hermes configuration snapshot to the live HERMES_HOME.

The managed snapshot is the policy owner: every apply deep-merges the managed
leaves over the live root config so managed values always win while user-set
preferences (keys the managed leaves never touch) survive. A rogue edit to a
managed value is corrected on the next apply. The snapshot git commit is
stamped for observability and kept in a .bak, but the stamp never gates
re-application.

Retired principal-layer state (the household-auth plugin entry and the
gateway multiplex/profile-routing settings) is migrated out of the live root
config on every apply, so old deployments converge to the native
messaging-control model without an operator hand-edit.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import yaml


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base; override wins on scalar/list conflicts."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


# MCP servers retired from the managed snapshot by a cutover (e.g. a custom
# adapter removed from the managed leaves) are migrated out of the live
# config explicitly here, one server at a time, so the persistent config
# converges without an operator hand-edit. This is not an allowlist
# relaxation: every other unmanaged server is still refused by the rogue-set
# validation below.
RETIRED_MCP_SERVERS = ("signal-share",)


def _migrate_retired_servers(config: dict, scope: str) -> None:
    """Remove retired MCP server entries from a merged surface, in place.

    Only servers explicitly listed in RETIRED_MCP_SERVERS are removed; any
    other unmanaged server is left untouched for the rogue-set validation to
    refuse. Logs only when an entry is actually removed.
    """
    servers = config.get("mcp_servers")
    if not isinstance(servers, dict):
        return
    for name in RETIRED_MCP_SERVERS:
        if name in servers:
            del servers[name]
            print(f"[config-apply] Migrated retired MCP server {name} out of {scope} config")
    if not servers:
        config.pop("mcp_servers", None)


def _managed_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("HERMES_MANAGED_DIR", "/opt/hermes-managed/current/services/hermes/managed"))


def _stamp_path() -> pathlib.Path:
    home = pathlib.Path(os.environ.get("HERMES_HOME", "/opt/data"))
    return home / ".managed-config-stamp"


def _current_commit() -> str:
    # git-sync (v4.x public contract) publishes each synced revision under a
    # "current" symlink whose target basename is the revision; .git layout is
    # an implementation detail, so stamp from the symlink first.
    managed = _managed_dir()
    for d in (managed, *managed.parents):
        link = d / "current"
        if link.is_symlink():
            target = os.readlink(link)
            return os.path.basename(target) if target else "unversioned"
    # Fallback for ordinary local checkouts. The lexical walk keeps a
    # relative gitdir: target anchored at the worktree top, not the resolved path.
    for d in (managed, *managed.parents):
        marker = d / ".git"
        if not marker.exists():
            continue
        if marker.is_file():
            target = marker.read_text(encoding="utf-8").strip().removeprefix("gitdir:").strip()
            if pathlib.Path(target).is_absolute():
                marker = pathlib.Path(target)
            else:
                marker = pathlib.Path(os.path.normpath(os.path.join(d, target)))
        head = marker / "HEAD"
        if head.exists():
            return head.read_text(encoding="utf-8").strip()
        return "unversioned"
    return "unversioned"


def _hermes_uid_gid() -> tuple[int, int]:
    # The gateway drops to this uid/gid (HERMES_UID/HERMES_GID); every file
    # config-apply installs as root must be readable by it.
    return (int(os.environ.get("HERMES_UID", "10000")), int(os.environ.get("HERMES_GID", "10000")))


def _sha256(path: pathlib.Path) -> bytes:
    import hashlib

    return hashlib.sha256(path.read_bytes()).digest()


def apply() -> None:
    home = pathlib.Path(os.environ.get("HERMES_HOME", "/opt/data"))
    managed = _managed_dir()
    if not (managed / "policy.yaml").exists():
        raise RuntimeError(f"managed snapshot missing at {managed}")

    commit = _current_commit()
    stamp = _stamp_path()
    # Always re-apply. The deep merge only overrides managed keys, so user-set
    # preferences survive, and managed values are re-asserted on every apply —
    # a rogue edit to a managed value (or a stale applied state) is corrected.
    # The stamp is informational only; it must not gate re-application.
    if stamp.exists() and stamp.read_text(encoding="utf-8").strip() == commit:
        print(f"[config-apply] Snapshot {commit} already applied; re-asserting managed values")

    config_path = home / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config = config or {}

    if config_path.exists():
        config_path.with_suffix(".yaml.bak").write_text(
            config_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    # Managed leaves, in merge order. Later leaves win on conflict. The base,
    # policy, integrations, and workspace instruction files are mandatory: a
    # missing file means the managed surface is incomplete, not benign absence.
    for leaf in ("base.yaml", "policy.yaml", "integrations.yaml"):
        if not (managed / leaf).exists():
            raise RuntimeError(f"mandatory leaf {leaf} missing")
    workspace_instructions = managed / "workspace" / "AGENTS.md"
    if not workspace_instructions.is_file():
        raise RuntimeError("mandatory workspace/AGENTS.md missing")
    integrations = yaml.safe_load((managed / "integrations.yaml").read_text(encoding="utf-8"))
    if not isinstance(integrations, dict) or not isinstance((integrations or {}).get("mcp_servers"), dict):
        raise RuntimeError("managed integrations leaf defines no mcp_servers set")

    # State from the retired principal layer lives only in old live configs.
    # Migrate it out before the managed merge so an old deployment converges
    # to the native guard model in one apply; everything else in these
    # sections survives untouched.
    plugins = config.get("plugins")
    if isinstance(plugins, dict) and isinstance(plugins.get("enabled"), list):
        if "household-auth" in plugins["enabled"]:
            plugins["enabled"] = [p for p in plugins["enabled"] if p != "household-auth"]
            print("[config-apply] Migrated retired household-auth plugin out of live config")
    gateway = config.get("gateway")
    if isinstance(gateway, dict):
        for key in ("multiplex_profiles", "multiplex_profile_allowlist", "profile_routes"):
            if key in gateway:
                gateway.pop(key)
                print(f"[config-apply] Migrated retired gateway.{key} out of live config")

    for leaf in ("base.yaml", "policy.yaml", "integrations.yaml"):
        leaf_path = managed / leaf
        if leaf_path.exists():
            leaf_data = yaml.safe_load(leaf_path.read_text(encoding="utf-8")) or {}
            _deep_merge(config, leaf_data)
            print(f"[config-apply] Merged {leaf}")

    # MCP server set is security-relevant. Deep merge is additive: it restores
    # managed values but cannot reject a rogue server an actor added to a live
    # config. The managed leaves are the only source of the allowed set. A
    # rogue entry is refused with a loud refusal: the healthcheck drops to
    # unhealthy and the tamper is visible in logs. The live config is left
    # untouched (the .yaml.bak written above is the recovery point); operator
    # removes the rogue server from the live config (or restores the .bak)
    # and the next apply re-validates. Legitimate tweaks to managed servers
    # survive the merge above.
    # Migrate explicitly retired servers out of the merged live surface before
    # validation so a retired entry from a past cutover converges on its own.
    _migrate_retired_servers(config, "root")
    root_allowed = set((integrations["mcp_servers"] or {}).keys())
    rogue = set((config.get("mcp_servers") or {}).keys()) - root_allowed
    if rogue:
        raise RuntimeError(
            f"rogue MCP server(s) {sorted(rogue)} in root config; allowed {sorted(root_allowed)}"
        )

    # Root surface clean: persist the root config as the runtime Hermes user
    # so dashboard/CLI preference edits remain possible.
    uid, gid = _hermes_uid_gid()
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    config_path.chmod(0o640)
    if os.getuid() == 0:
        os.chown(config_path, uid, gid)

    workspace = home / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    workspace_dst = workspace / "AGENTS.md"
    shutil.copyfile(workspace_instructions, workspace_dst)
    workspace_dst.chmod(0o644)
    if os.getuid() == 0:
        os.chown(workspace, uid, gid)
        os.chown(workspace_dst, uid, gid)
    print("[config-apply] Installed workspace instructions")

    # Canonical household skills: copy the managed skills tree into the home.
    # User-added skills are never touched; only the managed skill files are
    # (re)installed.
    managed_skills = managed / "skills"
    if managed_skills.exists():
        home_skills = home / "skills"
        home_skills.mkdir(parents=True, exist_ok=True)
        for skill_dir in managed_skills.rglob("SKILL.md"):
            rel = skill_dir.parent.relative_to(managed_skills)
            dst_dir = home_skills / rel
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(skill_dir, dst_dir / "SKILL.md")
            print(f"[config-apply] Installed skill {rel}")

    stamp.write_text(commit + "\n", encoding="utf-8")
    print(f"[config-apply] Applied snapshot {commit}")


def check() -> int:
    """Readiness check: validate the managed snapshot and the live root config.

    Exit 0 only when the snapshot is present and parseable, its mandatory
    leaves are all there, the workspace instructions match, the pinned MCP
    executables are installed, the live root config's MCP servers stay within
    the managed allowed set, and no retired principal-layer state remains.
    Used by the container healthcheck so the gateway never reports ready on
    an incomplete, tampered, or un-converged config.
    """
    home = pathlib.Path(os.environ.get("HERMES_HOME", "/opt/data"))
    managed = _managed_dir()
    if not (managed / "policy.yaml").exists():
        print(f"[config-apply] readiness FAILED: managed snapshot missing at {managed}", file=sys.stderr)
        return 1
    try:
        for leaf in ("base.yaml", "policy.yaml", "integrations.yaml"):
            if not (managed / leaf).exists():
                raise RuntimeError(f"mandatory leaf {leaf} missing")
        workspace_src = managed / "workspace" / "AGENTS.md"
        workspace_dst = home / "workspace" / "AGENTS.md"
        if not workspace_src.is_file():
            raise RuntimeError("mandatory workspace/AGENTS.md missing")
        if not workspace_dst.is_file() or _sha256(workspace_src) != _sha256(workspace_dst):
            raise RuntimeError("managed workspace instructions missing or tampered")
        for leaf in ("base.yaml", "policy.yaml", "integrations.yaml"):
            leaf_path = managed / leaf
            if leaf_path.exists():
                data = yaml.safe_load(leaf_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise RuntimeError(f"{leaf} is not a mapping")
        integrations = yaml.safe_load((managed / "integrations.yaml").read_text(encoding="utf-8")) or {}
        if not isinstance((integrations or {}).get("mcp_servers"), dict):
            raise RuntimeError("integrations.yaml defines no mcp_servers set")
        for executable in (
            home / "mcp" / "mealie-mcp-server" / ".venv" / "bin" / "mealie-mcp-server",
            home / "mcp" / "babybuddy-mcp" / ".venv" / "bin" / "babybuddy-mcp",
        ):
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise RuntimeError(f"pinned MCP executable missing or not executable: {executable}")

        # Live root config must stay inside the managed allowed set. This
        # catches a rogue server added at runtime (dashboard/CLI/direct edit)
        # even when apply() has not run since the tamper.
        root_allowed = set((integrations["mcp_servers"] or {}).keys())
        root_config = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8")) if (home / "config.yaml").exists() else {}
        root_config = root_config or {}
        rogue = set((root_config.get("mcp_servers") or {}).keys()) - root_allowed
        if rogue:
            raise RuntimeError(
                f"rogue MCP server(s) {sorted(rogue)} in live root config; allowed {sorted(root_allowed)}"
            )

        # Retired principal-layer state must be gone from the live root
        # config: the household-auth plugin entry and the gateway
        # multiplex/profile-routing settings are migrated out by apply().
        # A lingering entry means an apply has not converged since the
        # retirement, so readiness drops instead of running un-converged.
        plugins = root_config.get("plugins")
        if isinstance(plugins, dict) and "household-auth" in (plugins.get("enabled") or []):
            raise RuntimeError("retired household-auth plugin still enabled in live root config")
        gateway = root_config.get("gateway")
        if isinstance(gateway, dict):
            stale = [k for k in ("multiplex_profiles", "multiplex_profile_allowlist", "profile_routes") if k in gateway]
            if stale:
                raise RuntimeError(f"retired gateway settings {sorted(stale)} still present in live root config")
    except (RuntimeError, OSError, yaml.YAMLError) as exc:
        print(f"[config-apply] readiness FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"[config-apply] readiness OK ({_current_commit()})")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    try:
        apply()
    except RuntimeError as exc:
        print(f"[config-apply] REFUSING readiness: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
