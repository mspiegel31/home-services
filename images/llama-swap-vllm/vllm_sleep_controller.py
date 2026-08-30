#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence

REQUEST_PROGRAM = """
import sys
from urllib.request import Request, urlopen

method, path = sys.argv[1:]
request = Request(
    \"http://127.0.0.1:8000\" + path,
    data=b\"\" if method == \"POST\" else None,
    method=method,
)
with urlopen(request, timeout=30) as response:
    print(response.read().decode(), end=\"\")
"""


def run_docker(arguments: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *arguments],
        check=check,
        text=True,
        capture_output=True,
    )


def request(container: str, method: str, path: str) -> None:
    result = run_docker(
        ["exec", container, "python3", "-c", REQUEST_PROGRAM, method, path]
    )
    if result.stdout:
        sys.stdout.write(result.stdout)


def is_running(container: str) -> bool:
    result = run_docker(
        ["inspect", "--format", "{{.State.Running}}", container], check=False
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def is_healthy(container: str) -> bool:
    try:
        request(container, "GET", "/health")
    except subprocess.CalledProcessError:
        return False
    return True


def sleep_model(container: str, level: int) -> None:
    request(container, "POST", f"/sleep?level={level}")


def wait_for_health(
    container: str, timeout: int, stop_event: threading.Event
) -> None:
    deadline = time.monotonic() + timeout
    while not is_healthy(container):
        if stop_event.is_set():
            return
        if not is_running(container):
            raise RuntimeError(
                f"vLLM container {container} stopped before becoming healthy"
            )
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"vLLM container {container} was not healthy after {timeout}s"
            )
        stop_event.wait(1)


def serve(args: argparse.Namespace) -> None:
    start_command = args.start_command
    if start_command[:1] == ["--"]:
        start_command = start_command[1:]

    stop_event = threading.Event()
    sleep_on_stop = True

    def stop(signum: int, _frame: object) -> None:
        nonlocal sleep_on_stop
        sleep_on_stop = signum != signal.SIGUSR1
        stop_event.set()

    signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGUSR1, stop)

    if is_running(args.container):
        if not is_healthy(args.container):
            request(args.container, "POST", "/wake_up")
    else:
        run_docker(["rm", "--force", args.container], check=False)
        if not start_command:
            raise ValueError("serve requires a Docker run command after --")
        subprocess.run(start_command, check=True, text=True)

    wait_for_health(args.container, args.timeout, stop_event)
    if not stop_event.is_set():
        stop_event.wait()

    if sleep_on_stop:
        try:
            sleep_model(args.container, args.sleep_level)
        except subprocess.CalledProcessError:
            pass


def sleep(args: argparse.Namespace) -> None:
    sleep_model(args.container, args.sleep_level)
    os.kill(args.stop_pid, signal.SIGUSR1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    serve_parser = commands.add_parser("serve")
    serve_parser.add_argument("--container", required=True)
    serve_parser.add_argument("--timeout", type=int, default=3600)
    serve_parser.add_argument("--sleep-level", type=int, choices=(1, 2), default=1)
    serve_parser.add_argument("start_command", nargs=argparse.REMAINDER)
    serve_parser.set_defaults(handler=serve)

    sleep_parser = commands.add_parser("sleep")
    sleep_parser.add_argument("--container", required=True)
    sleep_parser.add_argument("--sleep-level", type=int, choices=(1, 2), default=1)
    sleep_parser.add_argument("--stop-pid", type=int, required=True)
    sleep_parser.set_defaults(handler=sleep)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
