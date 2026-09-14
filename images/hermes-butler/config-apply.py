#!/usr/bin/env python3
"""Apply the managed Hermes configuration snapshot to the live HERMES_HOME.

The managed snapshot is the policy owner: every apply deep-merges the managed
leaves over the live config so managed values always win while user-set
preferences (keys the managed leaves never touch) survive. A rogue edit to a
managed value is corrected on the next apply. The snapshot git commit is stamped
for observability and kept in a .bak, but the stamp never gates re-application.

Fails readiness (non-zero exit) when the mandatory household-auth principal
policy is absent or unbindable — the managed layer must own the authorization
config, and a missing allowlist is a readiness failure, not a permissive
fallback. User-mutable preference keys are never set by the managed leaves.
"""
from __future__ import annotations

import os
import pathlib
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


def _managed_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("HERMES_MANAGED_DIR", "/opt/hermes-managed"))


def _stamp_path() -> pathlib.Path:
    home = pathlib.Path(os.environ.get("HERMES_HOME", "/opt/data"))
    return home / ".managed-config-stamp"


def _current_commit() -> str:
    head = _managed_dir() / ".git" / "HEAD"
    if head.exists():
        return head.read_text(encoding="utf-8").strip()
    commit = _managed_dir() / ".commit"
    if commit.exists():
        return commit.read_text(encoding="utf-8").strip()
    return "unversioned"


def _load_principals(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    principals = data.get("principals") or {}
    if not principals:
        raise RuntimeError("principals file is empty")

    def ids(value) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, (list, tuple)):
            return tuple(str(v).strip() for v in value if str(v).strip())
        if isinstance(value, str):
            return tuple(v.strip() for v in value.split(",") if v.strip())
        return (str(value).strip(),)

    for name, entry in principals.items():
        if not ids(entry.get("sender_ids")):
            raise RuntimeError(f"principal {name} has no sender_ids")
    owners = [n for n, v in principals.items() if v.get("role") == "owner"]
    if len(owners) != 1:
        raise RuntimeError(f"exactly one owner required, got {sorted(owners)}")
    return principals


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

    # Managed leaves, in merge order. Later leaves win on conflict.
    # The profile and integrations leaves are mandatory: a missing leaf means
    # the managed surface is incomplete (an actor deleted it), which is a
    # policy loss, not a benign absence. Check before writing anything.
    for name in ("spouse", "family"):
        if not (managed / f"profile-{name}.yaml").exists():
            raise RuntimeError(f"mandatory profile leaf profile-{name}.yaml missing")
    if not (managed / "integrations.yaml").exists():
        raise RuntimeError("mandatory integrations leaf integrations.yaml missing")
    integrations = yaml.safe_load((managed / "integrations.yaml").read_text(encoding="utf-8"))
    if not isinstance(integrations, dict) or not isinstance((integrations or {}).get("mcp_servers"), dict):
        raise RuntimeError("managed integrations leaf defines no mcp_servers set")
    for leaf in ("policy.yaml", "profile-routes.yaml", "integrations.yaml"):
        leaf_path = managed / leaf
        if leaf_path.exists():
            leaf_data = yaml.safe_load(leaf_path.read_text(encoding="utf-8")) or {}
            _deep_merge(config, leaf_data)
            print(f"[config-apply] Merged {leaf}")

    # MCP server set is security-relevant. Deep merge is additive: it restores
    # managed values but cannot reject a rogue server an actor added to a live
    # config (root or per-profile). The managed leaves are the only source of
    # the allowed set. A rogue entry is refused with a loud refusal: the
    # healthcheck drops to unhealthy and the tamper is visible in logs. The
    # live config is left untouched (the .yaml.bak written above is the
    # recovery point); operator removes the rogue server from the live config
    # (or restores the .bak) and the next apply re-validates. Legitimate
    # tweaks to managed servers survive the merge above.
    root_allowed = set((integrations["mcp_servers"] or {}).keys())
    rogue = set((config.get("mcp_servers") or {}).keys()) - root_allowed
    if rogue:
        raise RuntimeError(
            f"rogue MCP server(s) {sorted(rogue)} in root config; allowed {sorted(root_allowed)}"
        )

    # Merge profile leaves in memory; validate each surface; then persist.
    # The root check above ran before any write, so a root refusal leaves the
    # live configs untouched (the .yaml.bak is the recovery point).
    profiles_dir = home / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    merged_profiles = {}
    for name in ("spouse", "family"):
        leaf_data = yaml.safe_load((managed / f"profile-{name}.yaml").read_text(encoding="utf-8")) or {}
        pconfig_path = profiles_dir / name / "config.yaml"
        pconfig = yaml.safe_load(pconfig_path.read_text(encoding="utf-8")) if pconfig_path.exists() else {}
        pconfig = pconfig or {}
        _deep_merge(pconfig, leaf_data)
        leaf_allowed = set(((leaf_data or {}).get("mcp_servers") or {}).keys())
        rogue = set((pconfig.get("mcp_servers") or {}).keys()) - leaf_allowed
        if rogue:
            raise RuntimeError(
                f"rogue MCP server(s) {sorted(rogue)} in profile {name}; allowed {sorted(leaf_allowed)}"
            )
        merged_profiles[name] = (pconfig, pconfig_path)

    # All surfaces clean: persist root and profile configs.
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    for name, (pconfig, pconfig_path) in merged_profiles.items():
        pconfig_path.write_text(yaml.safe_dump(pconfig, sort_keys=False), encoding="utf-8")
        print(f"[config-apply] Merged profile {name}")

    # Canonical household skills: copy the managed skills tree into the home so
    # every profile can read the shared care entry point. User-added skills are
    # never touched; only the managed skill files are (re)installed.
    managed_skills = managed / "skills"
    if managed_skills.exists():
        home_skills = home / "skills"
        home_skills.mkdir(parents=True, exist_ok=True)
        import shutil
        for skill_dir in managed_skills.rglob("SKILL.md"):
            rel = skill_dir.parent.relative_to(managed_skills)
            dst_dir = home_skills / rel
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(skill_dir, dst_dir / "SKILL.md")
            print(f"[config-apply] Installed skill {rel}")

    # Principal policy: copy managed principals into place and validate.
    principals_src = _principals_path(managed)
    principals_dst = home / "principals.yaml"
    principals_dst.write_text(principals_src.read_text(encoding="utf-8"), encoding="utf-8")
    os.chmod(principals_dst, 0o600)
    _load_principals(principals_dst)
    print("[config-apply] Principal policy validated and installed")

    stamp.write_text(commit + "\n", encoding="utf-8")
    print(f"[config-apply] Applied snapshot {commit}")


def _principals_path(managed: pathlib.Path) -> pathlib.Path:
    # The deployment binds real sender IDs in the snapshot's principals.yaml
    # (not the empty template); if only the template is present, fail closed.
    for name in ("principals.yaml", "principals.template.yaml"):
        p = managed / name
        if p.exists():
            return p
    raise RuntimeError("principals.yaml not found in managed snapshot")


def check() -> int:
    """Readiness check: validate the managed snapshot and the live effective config.

    Exit 0 only when the snapshot is present, its principal policy is valid,
    every restricted profile leaf is parseable, and the live config's MCP
    servers (root and per-profile) are a subset of the managed allowed sets.
    Used by the container healthcheck so the gateway never reports ready on
    an invalid, unbound, or tampered policy.
    """
    home = pathlib.Path(os.environ.get("HERMES_HOME", "/opt/data"))
    managed = _managed_dir()
    # Fail open when the snapshot is absent, matching the 03-managed-config
    # gate: the sync loop only runs after the container boots, so a missing
    # snapshot at first boot is "git-sync pending", not policy loss.
    if not (managed / "policy.yaml").exists():
        print("[config-apply] readiness OK (unmanaged: no managed snapshot yet)")
        return 0
    try:
        _load_principals(_principals_path(managed))
        # Mandatory-leaf rule mirrors apply(): policy.yaml is required by the
        # snapshot check; integrations and the per-profile leaves define the
        # bounded MCP surfaces and are mandatory. profile-routes.yaml is
        # optional. A missing mandatory leaf is policy loss.
        for leaf in ("integrations.yaml", "profile-spouse.yaml", "profile-family.yaml"):
            if not (managed / leaf).exists():
                raise RuntimeError(f"mandatory leaf {leaf} missing")
        for leaf in ("policy.yaml", "profile-routes.yaml", "integrations.yaml", "profile-spouse.yaml", "profile-family.yaml"):
            leaf_path = managed / leaf
            if leaf_path.exists():
                data = yaml.safe_load(leaf_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise RuntimeError(f"{leaf} is not a mapping")
        integrations = yaml.safe_load((managed / "integrations.yaml").read_text(encoding="utf-8")) or {}
        if not isinstance((integrations or {}).get("mcp_servers"), dict):
            raise RuntimeError("integrations.yaml defines no mcp_servers set")

        # Live effective surfaces must stay inside the managed allowed sets.
        # This catches a rogue server added at runtime (dashboard/CLI/direct
        # edit) even when apply() has not run since the tamper.
        root_allowed = set((integrations["mcp_servers"] or {}).keys())
        root_config = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8")) if (home / "config.yaml").exists() else {}
        rogue = set(((root_config or {}).get("mcp_servers") or {}).keys()) - root_allowed
        if rogue:
            raise RuntimeError(
                f"rogue MCP server(s) {sorted(rogue)} in live root config; allowed {sorted(root_allowed)}"
            )
        for name in ("spouse", "family"):
            leaf_data = yaml.safe_load((managed / f"profile-{name}.yaml").read_text(encoding="utf-8"))
            leaf_allowed = set(((leaf_data or {}).get("mcp_servers") or {}).keys())
            pconfig_path = home / "profiles" / name / "config.yaml"
            pconfig = yaml.safe_load(pconfig_path.read_text(encoding="utf-8")) if pconfig_path.exists() else {}
            rogue = set(((pconfig or {}).get("mcp_servers") or {}).keys()) - leaf_allowed
            if rogue:
                raise RuntimeError(
                    f"rogue MCP server(s) {sorted(rogue)} in live profile {name}; allowed {sorted(leaf_allowed)}"
                )
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
