#!/command/with-contenv /usr/bin/python3
"""Install locked household MCP projects into the persistent Hermes volume.

This runs after upstream ``01-hermes-setup`` remaps the Hermes UID and owns
``/opt/data``, but before any profile gateway can start.
"""

from __future__ import annotations

import os
import pwd
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

LOG_PREFIX = "[household-mcp-tools]"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data"))
PROJECTS_DIR = HERMES_HOME / "mcp"
UV_CACHE_DIR = HERMES_HOME / ".cache" / "uv"
STAMP_PATH = HERMES_HOME / ".household-mcp-projects"
PYTHON = "/usr/bin/python3.13"


@dataclass(frozen=True)
class McpProject:
    name: str
    repository: str
    revision: str
    executable: str

    @property
    def directory(self) -> Path:
        return PROJECTS_DIR / self.name

    @property
    def executable_path(self) -> Path:
        return self.directory / ".venv" / "bin" / self.executable


PROJECTS = (
    McpProject(
        name="mealie-mcp-server",
        repository="https://github.com/rldiao/mealie-mcp-server.git",
        revision="02183a84b92ba88e69fa11ded8b8235cc01771eb",
        executable="mealie-mcp-server",
    ),
    McpProject(
        name="babybuddy-mcp",
        repository="https://github.com/babybuddy/babybuddy-mcp.git",
        revision="9f32d446241c323602b23160d05e926161184d9f",
        executable="babybuddy-mcp",
    ),
)


def run_as_hermes(
    *command: object,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one command as the remapped runtime user with its persistent HOME."""
    return subprocess.run(
        [
            "/command/s6-setuidgid",
            "hermes",
            "env",
            f"HOME={HERMES_HOME}",
            *(str(part) for part in command),
        ],
        check=check,
        capture_output=capture_output,
        text=True,
    )


def current_revision(project: McpProject) -> str | None:
    if not (project.directory / ".git").is_dir():
        return None
    result = run_as_hermes(
        "git",
        "-C",
        project.directory,
        "rev-parse",
        "HEAD",
        check=False,
        capture_output=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def expected_stamp() -> str:
    return "".join(f"{project.name}={project.revision}\n" for project in PROJECTS)


def installation_is_current() -> bool:
    if not STAMP_PATH.is_file():
        return False
    if STAMP_PATH.read_text(encoding="utf-8") != expected_stamp():
        return False
    return all(
        project.executable_path.is_file()
        and os.access(project.executable_path, os.X_OK)
        and current_revision(project) == project.revision
        for project in PROJECTS
    )


def sync_project(project: McpProject) -> None:
    if current_revision(project) != project.revision:
        print(f"{LOG_PREFIX} Fetching {project.name}@{project.revision}", flush=True)
        run_as_hermes("rm", "-rf", project.directory)
        run_as_hermes("git", "init", project.directory)
        run_as_hermes(
            "git", "-C", project.directory, "remote", "add", "origin", project.repository
        )
        run_as_hermes(
            "git", "-C", project.directory, "fetch", "--depth", "1", "origin", project.revision
        )
        run_as_hermes(
            "git", "-C", project.directory, "checkout", "--detach", "FETCH_HEAD"
        )
        actual = current_revision(project)
        if actual != project.revision:
            raise RuntimeError(
                f"{project.name} checkout is {actual!r}, expected {project.revision}"
            )

    print(f"{LOG_PREFIX} Syncing locked {project.name} environment", flush=True)
    run_as_hermes(
        "env",
        f"UV_CACHE_DIR={UV_CACHE_DIR}",
        "uv",
        "sync",
        "--project",
        project.directory,
        "--frozen",
        "--no-dev",
        "--no-editable",
        "--python",
        PYTHON,
    )
    if not project.executable_path.is_file() or not os.access(
        project.executable_path, os.X_OK
    ):
        raise RuntimeError(
            f"{project.name} executable missing at {project.executable_path}"
        )


def write_stamp() -> None:
    temporary = STAMP_PATH.with_suffix(".tmp")
    temporary.write_text(expected_stamp(), encoding="utf-8")
    hermes = pwd.getpwnam("hermes")
    os.chown(temporary, hermes.pw_uid, hermes.pw_gid)
    temporary.chmod(0o644)
    temporary.replace(STAMP_PATH)


def main() -> int:
    try:
        if installation_is_current():
            print(f"{LOG_PREFIX} Pinned MCP projects already installed")
            return 0

        run_as_hermes("mkdir", "-p", PROJECTS_DIR, UV_CACHE_DIR)
        for project in PROJECTS:
            sync_project(project)
        write_stamp()
        print(f"{LOG_PREFIX} Pinned MCP projects ready")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"{LOG_PREFIX} REFUSING startup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
