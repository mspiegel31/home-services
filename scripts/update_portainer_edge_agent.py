#!/usr/bin/env python3
"""Upgrade the Portainer edge agent container on this host.

Pulls the new agent image first, then rebuilds the container while preserving
EDGE_ID, EDGE_KEY, and the /data volume so the endpoint stays associated with
Portainer. Run on the agent host as root (or a user in the docker group).

    python3 update_portainer_edge_agent.py --dry-run
    python3 update_portainer_edge_agent.py
    python3 update_portainer_edge_agent.py --image portainer/agent:2.45.0
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

FALLBACK_CONTAINER_NAME = "portainer_agent"
def run(args, check=True, quiet=False):
    if not quiet:
        print(f"$ {' '.join(args)}", flush=True)
    return subprocess.run(args, check=check, text=True, capture_output=quiet)


def die(message):
    sys.exit(f"error: {message}")


def docker(*args, check=True, quiet=False):
    return run(["docker", *args], check=check, quiet=quiet)


def inspect(name):
    raw = docker("inspect", name, quiet=True).stdout
    return json.loads(raw)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--image",
        default="portainer/agent:lts",
        help="agent image to deploy (default: %(default)s; pin a version like portainer/agent:2.45.0 to match the server)",
    )
    parser.add_argument(
        "--container",
        default="portainer_edge_agent",
        help="edge agent container name (default: %(default)s; falls back to portainer_agent if not found)",
    )
    parser.add_argument(
        "--edge-key",
        default=None,
        help="override EDGE_KEY (base64 blob from Portainer: Environment -> Edge information). "
        "Used only if the running container does not expose one.",
    )
    parser.add_argument(
        "--insecure-poll",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="set EDGE_INSECURE_POLL=1 (needed while the Portainer server uses a self-signed cert; default: on)",
    )
    parser.add_argument("--dry-run", action="store_true", help="show the docker run command without changing anything")
    args = parser.parse_args()

    if not shutil.which("docker"):
        die("docker CLI not found in PATH")

    name = args.container
    exists = docker("inspect", name, check=False, quiet=True)
    if exists.returncode != 0:
        if docker("inspect", FALLBACK_CONTAINER_NAME, check=False, quiet=True).returncode == 0:
            print(f"{name} not found; using {FALLBACK_CONTAINER_NAME}")
            name = FALLBACK_CONTAINER_NAME
        else:
            die(f"no portainer agent container found (tried {name} and {FALLBACK_CONTAINER_NAME})")

    spec = inspect(name)
    env = dict(v.split("=", 1) for v in spec["Config"]["Env"] if "=" in v)
    edge_id = env.get("EDGE_ID")
    edge_key = args.edge_key or env.get("EDGE_KEY")
    if not edge_id:
        die("running container has no EDGE_ID env var — this is not an edge agent. Aborting.")
    if not edge_key:
        die("no EDGE_KEY found. Get it from Portainer (Environment -> edge -> Edge information) and pass --edge-key.")

    mounts = spec["Mounts"]
    data_volume = next((m["Name"] for m in mounts if m.get("Type") == "volume" and m["Destination"] == "/data"), None)
    if not data_volume:
        die("running container has no /data volume; the edge key would be lost on rebuild. Aborting.")

    bind_mounts = [m for m in mounts if m.get("Type") == "bind"]
    docker_root = "/var/lib/docker/volumes"
    for m in bind_mounts:
        if m["Destination"] == "/var/lib/docker/volumes":
            # Truenas SCALE (and friends) relocate /var/lib/docker to a pool path;
            # mount the resolved target so host-side volume paths keep working.
            docker_root = os.path.realpath(m["Source"])
            break

    volume_args = []
    for m in bind_mounts:
        if m["Destination"] == "/var/lib/docker/volumes":
            volume_args += ["-v", f"{docker_root}:/var/lib/docker/volumes"]
        else:
            volume_args += ["-v", f"{m['Source']}:{m['Destination']}"]
    volume_args += ["-v", f"{data_volume}:/data"]

    env_args = ["-e", "EDGE=1", "-e", f"EDGE_ID={edge_id}", "-e", f"EDGE_KEY={edge_key}"]
    if args.insecure_poll:
        env_args += ["-e", "EDGE_INSECURE_POLL=1"]

    run_cmd = [
        "docker",
        "run",
        "-d",
        *volume_args,
        *env_args,
        "--restart",
        "always",
        "--name",
        name,
        args.image,
    ]

    print(f"\nrebuilding {name}:")
    print(f"  image:        {args.image}")
    print(f"  EDGE_ID:      {edge_id}")
    print(f"  EDGE_KEY:     <{len(edge_key)} chars, from {'--edge-key' if args.edge_key else 'existing container'}>")
    print(f"  data volume:  {data_volume}")
    print(f"  docker root:  {docker_root}")
    if args.insecure_poll:
        print("  EDGE_INSECURE_POLL=1")
    print(f"\n$ {' '.join(run_cmd)}\n")

    if args.dry_run:
        print("dry run — nothing changed.")
        return

    print("pulling image...")
    docker("pull", args.image)

    print(f"stopping and removing {name}...")
    docker("stop", name)
    docker("rm", name)

    print("starting new agent...")
    run(run_cmd)

    state = docker("inspect", "--format", "{{.State.Status}}", name, quiet=True).stdout.strip()
    if state != "running":
        print("\ncontainer is not running. Last log lines:", file=sys.stderr)
        docker("logs", "--tail", "20", name, check=False)
        die(
            "new agent container failed to start — Portainer endpoint data is intact "
            "(data volume preserved); re-run with the previous --image tag to roll back"
        )

    for _ in range(30):
        logs = docker("logs", "--tail", "50", name, check=False, quiet=True).stdout
        if any(word in logs.lower() for word in ("poll", "tunnel", "connected")):
            print(f"\nagent is up (state={state}). Confirm the heartbeat in Portainer within ~1 minute.")
            return
        time.sleep(2)

    print(
        f"\nagent is running (state={state}) but no poll activity seen in logs yet.\n"
        "Confirm the environment shows a live heartbeat in Portainer (default 5s poll)."
    )


if __name__ == "__main__":
    main()
