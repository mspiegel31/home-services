#!/usr/bin/env python3
"""Assemble Portainer stack deep links from stack/endpoint IDs.

Pure formatter: no network, no credentials. Portainer's UI routes on the client
(ui-router behind a `#!/` hash), so neither the API nor the MCP tools return
these links -- you build them from a stack's Id and EndpointId, which
StackList/StackInspect do return.

Feed it the MCP's StackList output, selected down to three fields:
    select="[].{id:Id,name:Name,endpoint:EndpointId}"
"""

import argparse
import json
import os
import sys

DEFAULT_BASE = os.environ.get("PORTAINER_URL", "https://192.168.1.51:9443")

# Stack type as it reaches the URL query string. The view rejects anything
# outside 1|2|3 with an "Invalid type URL parameter" toast.
TYPES = {"compose": "2", "swarm": "1", "kubernetes": "3"}

EXAMPLES = """examples:
  ./portainer_stack_url.py glance --id 218 --endpoint 2
  ./portainer_stack_url.py --json - --label        # pipe StackList JSON
  ./portainer_stack_url.py plex --id 220 --endpoint 25 --tab editor
"""


def build(name, stack_id, endpoint_id, stack_type="2", tab=None,
          container=None, external=False, orphaned=False, base=DEFAULT_BASE):
    """Return one stack deep link.

    `id` is what the page fetches the stack by and `name` is display-only, so
    the two must describe the same stack. The regular/orphaned/external flag
    gates the data fetch: without a true one the page renders an empty info tab
    that reads as a broken stack rather than a broken link.
    """
    flag = "external" if external else "orphaned" if orphaned else "regular"
    query = [f"id={stack_id}", f"type={stack_type}", f"{flag}=true"]
    if tab:
        query.append(f"tab={tab}")
    path = f"/docker/stacks/{name}"
    if container:
        path += f"/{container}"
    return f"{base.rstrip('/')}/#!/{endpoint_id}{path}?{'&'.join(query)}"


def rows_from_json(source):
    """Yield (name, id, endpoint) from a StackList-shaped JSON document."""
    for key in ("result", "items", "data"):
        if isinstance(source, dict) and isinstance(source.get(key), list):
            source = source[key]
            break
    if isinstance(source, dict):
        source = [source]
    for row in source:
        name = row.get("name") or row.get("Name")
        stack_id = row.get("id", row.get("Id"))
        endpoint = row.get("endpoint", row.get("EndpointId"))
        if not (name and stack_id is not None and endpoint is not None):
            raise SystemExit(f"error: row missing name/id/endpoint: {row!r}")
        yield name, stack_id, endpoint


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("name", nargs="?", help="stack name (display segment)")
    parser.add_argument("--id", type=int, help="stack Id")
    parser.add_argument("--endpoint", type=int, help="environment (endpoint) Id")
    parser.add_argument("--json", metavar="FILE",
                        help="read [{id,name,endpoint},...] from FILE, or - for stdin")
    parser.add_argument("--type", default="compose", choices=sorted(TYPES),
                        help="stack type (default: compose)")
    parser.add_argument("--tab", choices=["info", "editor"],
                        help="open a specific tab (default: info)")
    parser.add_argument("--container", help="deep link into a container of the stack")
    parser.add_argument("--external", action="store_true", help="external stack")
    parser.add_argument("--orphaned", action="store_true", help="orphaned stack")
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help=f"Portainer base URL (default: {DEFAULT_BASE})")
    parser.add_argument("--label", action="store_true",
                        help="prefix each URL with env/name (id)")
    args = parser.parse_args()

    if bool(args.name) == bool(args.json):
        parser.error("give either NAME --id --endpoint, or --json FILE")
    if args.name and not (args.id and args.endpoint):
        parser.error("NAME requires --id and --endpoint")

    if args.name:
        rows = [(args.name, args.id, args.endpoint)]
    else:
        try:
            handle = sys.stdin if args.json == "-" else open(args.json)
            source = json.load(handle)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: not JSON: {exc}")
        rows = list(rows_from_json(source))
        if not rows:
            raise SystemExit("error: no stacks in input")

    for name, stack_id, endpoint in rows:
        url = build(name, stack_id, endpoint, TYPES[args.type], args.tab,
                    args.container, args.external, args.orphaned, args.base)
        print(f"{endpoint}/{name} ({stack_id})\t{url}" if args.label else url)


if __name__ == "__main__":
    main()
