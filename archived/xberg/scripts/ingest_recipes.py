#!/usr/bin/env python3
"""Bridge: cookbook scans (Xberg) -> Mealie.

Reads scan files from SCAN_DIR, sends each to Xberg's /extract endpoint
(structured extraction uses the recipe schema defined in the server's
xberg.toml), dedups against Mealie by name, and POSTs new recipes to Mealie.

Python 3 stdlib only. Run on the host that can reach both Xberg and Mealie.

Env:
  XBERG_URL            (default http://127.0.0.1:8999)
  MEALIE_URL           (default http://192.168.1.39:9000)
  XBERG_MEALIE_TOKEN   (required)
  SCAN_DIR             (default /mnt/tank/container-configs/xberg/scan-inbox)

CLI:
  python3 ingest_recipes.py [--dir SCAN_DIR] [--dry-run]

Exit 0 if all files processed (skips/exists/fails included);
exit 1 only if xberg or mealie base URL is unreachable at start.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

SCAN_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def http_json(url, data=None, headers=None, method=None, timeout=600):
    """POST/GET JSON; returns parsed JSON body. Raises on non-2xx."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8")) if body else None


def http_check_base(url, timeout=10):
    """Return True if the base URL answers anything (any HTTP status)."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True  # server answered, just not 200
    except Exception:
        return False


def multipart_extract(xberg_url, filename, file_bytes):
    """POST a single file to Xberg /extract as multipart; return parsed JSON.

    Sends no `config` field: a request-scope config *replaces* the server
    config, it does not merge into it. Sending one would drop the server
    config's structured_extraction block (and with it the LLM routing), and
    the caller is not allowed to re-supply the credentials
    ("Caller extraction config may not set structured_extraction.llm.api_key").
    OCR forcing and output format therefore live in xberg.toml.
    """
    boundary = uuid.uuid4().hex
    lines = [
        f"--{boundary}",
        f'Content-Disposition: form-data; name="files"; filename="{filename}"',
        "Content-Type: application/octet-stream",
    ]
    head = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = head + file_bytes + tail

    req = urllib.request.Request(
        xberg_url.rstrip("/") + "/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1800) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mealie_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def mealie_name_exists(mealie_url, token, title):
    """Dedup by exact name via queryFilter."""
    q = urllib.parse.urlencode(
        {"queryFilter": f'name = "{title}"', "perPage": "1"}
    )
    url = f"{mealie_url.rstrip('/')}/api/recipes?{q}"
    data = http_json(url, headers=mealie_headers(token))
    return bool(data) and (data.get("total") or 0) > 0


def to_mealie_body(recipe, filename):
    """Map the xberg structured recipe object onto Mealie's Recipe body."""
    ingredients = []
    for ing in recipe.get("ingredients") or []:
        quantity = ing.get("quantity")
        unit = ing.get("unit")
        if quantity is None:
            quantity = 1
            disable_amount = True
        else:
            disable_amount = False
        ingredients.append(
            {
                "quantity": quantity,
                "unit": {"name": unit} if unit else None,
                "food": {"name": ing.get("name", "")},
                "note": ing.get("note") or "",
                "disable_amount": disable_amount,
            }
        )

    steps = [{"text": s.get("text", "")} for s in recipe.get("steps") or []]

    return {
        "name": recipe.get("title", ""),
        "description": recipe.get("description") or "",
        "recipeYield": recipe.get("servings") or "",
        "prepTime": recipe.get("prep_time"),
        "cookTime": recipe.get("cook_time"),
        "recipe_ingredient": ingredients,
        "recipe_instructions": steps,
        "tags": recipe.get("tags") or [],
        "recipe_category": recipe.get("categories") or [],
        "extras": {"source_file": filename},
    }


def structured_output_from_response(resp):
    """Pull results[0].structured_output; None when missing/errored."""
    results = (resp or {}).get("results") or []
    if not results:
        return None
    first = results[0]
    if (first or {}).get("error"):
        return None
    structured = first.get("structured_output")
    if not structured:
        return None
    if not structured.get("title") or not structured.get("steps"):
        return None
    return structured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        default=os.environ.get(
            "SCAN_DIR", "/mnt/tank/container-configs/xberg/scan-inbox"
        ),
        help="Folder of scan files (default: $SCAN_DIR)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stop after extraction; print would-be Mealie body; no dedup, no POST",
    )
    args = parser.parse_args()

    xberg_url = os.environ.get("XBERG_URL", "http://127.0.0.1:8999")
    mealie_url = os.environ.get("MEALIE_URL", "http://192.168.1.39:9000")
    token = os.environ.get("XBERG_MEALIE_TOKEN", "")
    if not args.dry_run and not token:
        print("ERROR: XBERG_MEALIE_TOKEN is required (omit in --dry-run)", file=sys.stderr)
        return 1

    scan_dir = Path(args.dir)
    if not scan_dir.is_dir():
        print(f"ERROR: scan dir not found: {scan_dir}", file=sys.stderr)
        return 1

    # Fail fast if base URLs are unreachable (skip mealie check in dry-run).
    if not http_check_base(xberg_url):
        print(f"ERROR: xberg unreachable at {xberg_url}", file=sys.stderr)
        return 1
    if not args.dry_run and not http_check_base(mealie_url):
        print(f"ERROR: mealie unreachable at {mealie_url}", file=sys.stderr)
        return 1

    # Schema, LLM routing, API key, force_ocr and output format all live in the
    # server's xberg.toml. The request deliberately sends no `config` field —
    # see multipart_extract().
    files = sorted(
        p
        for p in scan_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SCAN_EXTENSIONS
    )
    if not files:
        print(f"NO FILES: {scan_dir} has no *.pdf/*.jpg/*.jpeg/*.png")
        return 0

    for path in files:
        try:
            file_bytes = path.read_bytes()
            resp = multipart_extract(xberg_url, path.name, file_bytes)
            recipe = structured_output_from_response(resp)
            if recipe is None:
                print(f"SKIP {path.name}: no structured output")
                continue

            body = to_mealie_body(recipe, path.name)
            if args.dry_run:
                print(f"DRY-RUN {path.name}:")
                print(json.dumps(body, indent=2))
                continue

            title = body["name"]
            if mealie_name_exists(mealie_url, token, title):
                print(f"EXISTS {title}")
                continue

            url = f"{mealie_url.rstrip('/')}/api/recipes"
            data = http_json(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=mealie_headers(token),
                method="POST",
            )
            slug = data if isinstance(data, str) else (data or {}).get("slug", "?")
            print(f"CREATED {title} -> {slug}")
        except Exception as exc:  # per-file isolation; batch continues
            print(f"FAIL {path.name}: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
