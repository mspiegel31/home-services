from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

MAX_MESSAGE_LENGTH = 4_096
_FORBIDDEN_ALLOWLIST_VALUES = frozenset({"*", "all", "any"})

mcp = FastMCP("signal-share", instructions="Approval-gated Signal sharing to operator-configured targets.")


def parse_allowlist(raw: str) -> frozenset[str]:
    values = frozenset(value.strip() for value in raw.split(",") if value.strip())
    if any(value.casefold() in _FORBIDDEN_ALLOWLIST_VALUES for value in values):
        raise ValueError("Signal share allowlists must contain explicit targets")
    return values


def validate_share(
    target_type: str,
    target: str,
    message: str,
    *,
    allowed_users: frozenset[str],
    allowed_groups: frozenset[str],
) -> tuple[str, str, str]:
    normalized_type = target_type.strip().casefold()
    normalized_target = target.strip()
    normalized_message = message.strip()

    if normalized_type not in {"user", "group"}:
        raise ValueError("target_type must be 'user' or 'group'")
    if not normalized_target or normalized_target.casefold() in _FORBIDDEN_ALLOWLIST_VALUES:
        raise ValueError("target must be an explicit Signal user or group identifier")
    if not normalized_message:
        raise ValueError("message must not be empty")
    if len(normalized_message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"message exceeds {MAX_MESSAGE_LENGTH} characters")

    allowlist = allowed_users if normalized_type == "user" else allowed_groups
    if normalized_target not in allowlist:
        raise PermissionError("target is not in the configured Signal share allowlist")

    return normalized_type, normalized_target, normalized_message


def signal_rpc_url(raw: str) -> str:
    parsed = urllib.parse.urlparse(raw.strip())
    if (
        parsed.scheme != "http"
        or parsed.hostname != "signal-cli"
        or parsed.port != 8080
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("SIGNAL_HTTP_URL must be http://signal-cli:8080")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("SIGNAL_HTTP_URL must not contain credentials, query, or fragment")
    return "http://signal-cli:8080/api/v1/rpc"


def call_signal_rpc(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.load(response)
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("Signal delivery failed") from exc

    if not isinstance(body, dict) or body.get("error") is not None or "result" not in body:
        raise RuntimeError("Signal delivery failed")
    return body


@mcp.tool(
    annotations=ToolAnnotations(
        title="Share Signal message",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    )
)
def share_signal_message(
    target_type: Literal["user", "group"],
    target: str,
    message: str,
) -> dict[str, object]:
    """Share one message after Hermes shows the exact target and content for approval."""
    normalized_type, normalized_target, normalized_message = validate_share(
        target_type,
        target,
        message,
        allowed_users=parse_allowlist(os.environ.get("HERMES_SIGNAL_SHARE_USERS", "")),
        allowed_groups=parse_allowlist(os.environ.get("HERMES_SIGNAL_SHARE_GROUPS", "")),
    )

    params: dict[str, object] = {
        "account": os.environ["SIGNAL_ACCOUNT"].strip(),
        "message": normalized_message,
    }
    if not params["account"]:
        raise ValueError("SIGNAL_ACCOUNT must not be empty")
    if normalized_type == "user":
        params["recipient"] = [normalized_target]
    else:
        params["groupId"] = normalized_target

    response = call_signal_rpc(
        signal_rpc_url(os.environ.get("SIGNAL_HTTP_URL", "")),
        {"jsonrpc": "2.0", "method": "send", "params": params, "id": str(uuid.uuid4())},
    )
    result = response["result"]
    timestamp = result.get("timestamp") if isinstance(result, dict) else None
    return {"status": "sent", "target_type": normalized_type, "target": normalized_target, "timestamp": timestamp}


if __name__ == "__main__":
    mcp.run(transport="stdio")
