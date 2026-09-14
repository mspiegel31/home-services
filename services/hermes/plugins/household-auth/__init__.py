"""household-auth: sender-bound principal policy for the pinned Hermes gateway.

Closes the v2026.9.7 WhatsApp group-admission gap (an allowlisted group accepts any
participant) and blocks owner-only configuration mutations from non-owners. Native
platform_toolsets already restrict tools per profile; this plugin is the second
layer that binds a verified sender to a principal and denies the untrusted path.

Config: HERMES_HOUSEHOLD_PRINCIPALS points to a YAML file with a principals map.
Each principal has role, profile, and sender_ids. Exactly one owner is required.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger("household-auth")

_FORBIDDEN_TOOLS = frozenset({
    "terminal", "terminal_exec", "write", "edit", "file_write", "file_edit",
    "config", "config_set", "model", "plugins", "plugin_install", "plugin_update",
    "reload", "reload_mcp", "process_manage", "execute_code",
})
_PATH_RE = re.compile(
    r"^(?:/)?(?:etc/hermes|opt/data)\b|(?:^|/)(?:config\.ya?ml|\.env)\b",
    re.IGNORECASE,
)
_TEXT_RE = re.compile(
    r"(?:config(?:uration)?\s+(?:file|value|key)|change\s+(?:the\s+|my\s+)?(?:default\s+)?model|"
    r"set\s+(?:the\s+)?(?:default\s+)?model|edit\s+(?:the\s+)?config|write\s+(?:the\s+)?config|"
    r"/model\s+\S+\s+--global)",
    re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"(?:^|[^a-z0-9_])(?:config|config_set|model|terminal|terminal_exec|edit|write|file_write|"
    r"file_edit|plugins|plugin_install|plugin_update|reload|reload_mcp|process_manage|execute_code)(?:$|[^a-z0-9_])",
    re.IGNORECASE,
)


class HouseholdAuthError(RuntimeError):
    pass


def _coerce_ids(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    if isinstance(value, str):
        return tuple(v.strip() for v in value.split(",") if v.strip())
    return (str(value).strip(),)


def _resolve(user_id: Any, user_id_alt: Any) -> set[str]:
    identifiers = {str(v) for v in (user_id, user_id_alt) if v}
    resolved: set[str] = set()
    for identifier in identifiers:
        try:
            from gateway.whatsapp_identity import canonical_whatsapp_identifier, expand_whatsapp_aliases
            resolved.update(expand_whatsapp_aliases(canonical_whatsapp_identifier(identifier)))
        except Exception:
            resolved.add(identifier)
    return resolved


def _load_principals() -> Dict[str, Any]:
    path = os.environ.get("HERMES_HOUSEHOLD_PRINCIPALS")
    if not path or not os.path.exists(path):
        raise HouseholdAuthError("HERMES_HOUSEHOLD_PRINCIPALS is required and must be readable")
    data = yaml.safe_load(open(path)) or {}
    principals = data.get("principals") or {}
    if not principals:
        raise HouseholdAuthError("principals file is empty")
    for name, value in principals.items():
        if not _coerce_ids(value.get("sender_ids")):
            raise HouseholdAuthError(f"principal {name} has no sender_ids")
        if not isinstance(value.get("role"), str):
            raise HouseholdAuthError(f"principal {name} lacks a role")
    owners = {n for n, v in principals.items() if v.get("role") == "owner"}
    if len(owners) != 1:
        raise HouseholdAuthError(f"exactly one owner required, got {sorted(owners)}")
    return principals


def _is_config_mutation(tool_name: str, args_text: str) -> bool:
    name = re.sub(r"^mcp[_-]", "", str(tool_name or "").lower())
    if name in _FORBIDDEN_TOOLS:
        return True
    if _NAME_RE.search(name):
        return True
    if _PATH_RE.search(args_text) or _TEXT_RE.search(args_text):
        return True
    return False


def register(ctx: Any) -> None:
    principals = _load_principals()
    owner = next(n for n, v in principals.items() if v.get("role") == "owner")

    def _principal(user_id: Any, user_id_alt: Any, platform: str, profile: str) -> Optional[str]:
        if platform == "api_server":
            owner_profile = principals[owner].get("profile") or "owner-private"
            return "owner" if profile == owner_profile else None
        resolved = _resolve(user_id, user_id_alt)
        for name, bindings in principals.items():
            if resolved.intersection(set(_coerce_ids(bindings.get("sender_ids")))):
                return name
        return None

    def on_pre_gateway_dispatch(*, event: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        source = getattr(event, "source", None)
        platform = str(getattr(getattr(source, "platform", None), "value", "") or "")
        if platform != "whatsapp":
            return None
        if str(getattr(source, "chat_type", "dm")) != "group":
            return None
        if _principal(source.user_id, getattr(source, "user_id_alt", None), "whatsapp", None) is None:
            return {"action": "skip", "reason": "unknown_group_participant"}
        return None

    def on_pre_tool_call(*, tool_name: str = "", args: Any = None, **kwargs: Any) -> Optional[Dict[str, Any]]:
        text = args if isinstance(args, str) else (json.dumps(args, sort_keys=True) if args is not None else "")
        if not _is_config_mutation(tool_name, text):
            return None
        from gateway.session_context import get_session_env
        platform = str(get_session_env("HERMES_SESSION_PLATFORM") or "")
        profile = str(get_session_env("HERMES_SESSION_PROFILE") or "")
        principal = _principal(
            get_session_env("HERMES_SESSION_USER_ID"),
            get_session_env("HERMES_SESSION_USER_ID_ALT"),
            platform,
            profile,
        )
        if principal != owner:
            return {"action": "block", "message": "Configuration changes require the owner identity."}
        return None

    ctx.register_hook("pre_gateway_dispatch", on_pre_gateway_dispatch)
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
