#!/command/with-contenv /usr/bin/python3
"""Apply the Git-managed household snapshot before gateways start."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

LOG_PREFIX = "[household-config]"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data"))
MANAGED_DIR = Path(os.environ.get("HERMES_MANAGED_DIR", "/opt/hermes-managed/current"))
CONFIG_APPLIER = MANAGED_DIR / "init" / "config-apply.py"
PYTHON = "/opt/hermes/.venv/bin/python3"


def require_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"required file missing: {path}")


def main() -> int:
    try:
        require_file(MANAGED_DIR / "policy.yaml")
        require_file(CONFIG_APPLIER)

        environment = os.environ.copy()
        environment["HERMES_HOME"] = str(HERMES_HOME)
        environment["HERMES_MANAGED_DIR"] = str(MANAGED_DIR)
        result = subprocess.run(
            [PYTHON, str(CONFIG_APPLIER)],
            env=environment,
            check=False,
        )
        return result.returncode
    except (OSError, RuntimeError) as error:
        print(f"{LOG_PREFIX} REFUSING startup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
