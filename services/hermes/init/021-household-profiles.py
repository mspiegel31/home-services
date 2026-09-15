#!/command/with-contenv /usr/bin/python3
"""Create native household profiles before s6 starts gateway services."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

LOG_PREFIX = "[household-profiles]"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data"))
PROFILE_NAMES = ("spouse", "family")


def create_profile(name: str) -> None:
    profile = HERMES_HOME / "profiles" / name
    if (profile / "SOUL.md").is_file():
        return
    if profile.exists():
        raise RuntimeError(f"incomplete native profile at {profile}")

    print(f"{LOG_PREFIX} Creating native profile {name}", flush=True)
    subprocess.run(
        [
            "/command/s6-setuidgid",
            "hermes",
            "env",
            f"HOME={HERMES_HOME}",
            f"HERMES_HOME={HERMES_HOME}",
            "hermes",
            "profile",
            "create",
            name,
            "--clone",
            "--no-alias",
        ],
        check=True,
    )


def main() -> int:
    try:
        for name in PROFILE_NAMES:
            create_profile(name)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"{LOG_PREFIX} REFUSING startup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
