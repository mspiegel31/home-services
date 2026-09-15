from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

MAX_COMMENT_LENGTH = 5_000
MAX_SLUG_LENGTH = 255
_MISSING = object()

mcp = FastMCP("mealie-feedback", instructions="Bounded Mealie rating, favorite, and comment operations.")

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)


def mealie_base_url(raw: str) -> str:
    parsed = urllib.parse.urlparse(raw.strip())
    if (
        parsed.scheme != "http"
        or parsed.hostname != "mealie"
        or parsed.port != 9000
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("MEALIE_BASE_URL must be http://mealie:9000")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("MEALIE_BASE_URL must not contain credentials, query, or fragment")
    return "http://mealie:9000"


def normalize_slug(slug: str) -> str:
    value = slug.strip()
    if not value or len(value) > MAX_SLUG_LENGTH or any(ord(char) < 32 for char in value):
        raise ValueError("recipe slug is empty or invalid")
    return value


def normalize_comment(text: str) -> str:
    value = text.strip()
    if not value or len(value) > MAX_COMMENT_LENGTH:
        raise ValueError(f"comment must contain 1-{MAX_COMMENT_LENGTH} characters")
    return value


def normalize_uuid(value: str, field: str) -> str:
    try:
        return str(uuid.UUID(value.strip()))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} must be a UUID") from exc


def request_mealie(method: str, path: str, payload: object = _MISSING) -> Any:
    base_url = mealie_base_url(os.environ.get("MEALIE_BASE_URL", ""))
    token = os.environ.get("MEALIE_API_KEY", "").strip()
    if not token:
        raise ValueError("MEALIE_API_KEY must not be empty")

    data = None if payload is _MISSING else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Mealie request failed with HTTP {exc.code}") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError("Mealie request failed") from exc

    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Mealie returned an invalid response") from exc


def current_user_id() -> str:
    result = request_mealie("GET", "/api/users/self")
    if not isinstance(result, dict) or not isinstance(result.get("id"), str):
        raise RuntimeError("Mealie did not return the current user id")
    return normalize_uuid(result["id"], "current user id")


def recipe_id(slug: str) -> str:
    encoded_slug = urllib.parse.quote(normalize_slug(slug), safe="")
    result = request_mealie("GET", f"/api/recipes/{encoded_slug}")
    if not isinstance(result, dict) or not isinstance(result.get("id"), str):
        raise RuntimeError("Mealie did not return the recipe id")
    return normalize_uuid(result["id"], "recipe id")


@mcp.tool(annotations=WRITE)
def set_recipe_rating(slug: str, rating: float) -> dict[str, object]:
    """Set the current Mealie user's rating for a recipe from 0 through 5."""
    numeric_rating = float(rating)
    if not math.isfinite(numeric_rating) or numeric_rating < 0 or numeric_rating > 5:
        raise ValueError("rating must be between 0 and 5")
    encoded_slug = urllib.parse.quote(normalize_slug(slug), safe="")
    request_mealie(
        "POST",
        f"/api/users/{current_user_id()}/ratings/{encoded_slug}",
        {"rating": numeric_rating},
    )
    return {"status": "rated", "slug": normalize_slug(slug), "rating": numeric_rating}


@mcp.tool(annotations=WRITE)
def add_recipe_favorite(slug: str) -> dict[str, str]:
    """Add a recipe to the current Mealie user's favorites; removal is intentionally unavailable."""
    normalized_slug = normalize_slug(slug)
    encoded_slug = urllib.parse.quote(normalized_slug, safe="")
    request_mealie("POST", f"/api/users/{current_user_id()}/favorites/{encoded_slug}", {})
    return {"status": "favorited", "slug": normalized_slug}


@mcp.tool(annotations=READ_ONLY)
def get_recipe_comments(slug: str) -> Any:
    """Read comments for one Mealie recipe."""
    encoded_slug = urllib.parse.quote(normalize_slug(slug), safe="")
    return request_mealie("GET", f"/api/recipes/{encoded_slug}/comments")


@mcp.tool(annotations=WRITE)
def add_recipe_comment(slug: str, text: str) -> Any:
    """Add a comment to one Mealie recipe."""
    return request_mealie(
        "POST",
        "/api/comments",
        {"recipeId": recipe_id(slug), "text": normalize_comment(text)},
    )


@mcp.tool(annotations=WRITE)
def update_recipe_comment(comment_id: str, text: str) -> Any:
    """Update an existing Mealie comment; deletion is intentionally unavailable."""
    normalized_id = normalize_uuid(comment_id, "comment_id")
    return request_mealie(
        "PUT",
        f"/api/comments/{urllib.parse.quote(normalized_id, safe='')}",
        {"id": normalized_id, "text": normalize_comment(text)},
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
