"""Run the local API and dashboard together in the foreground."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

from argusfinance.config import Settings

_API_HOST = "127.0.0.1"
_DASHBOARD_HOST = "127.0.0.1"
_DASHBOARD_PORT = 5173
_DASHBOARD_API_PORT_ENV = "ARGUS_DASHBOARD_API_PORT"
_TERMINATE_TIMEOUT_SECONDS = 5.0
_KILL_TIMEOUT_SECONDS = 5.0


def _normalize_returncode(returncode: int) -> int:
    return 128 - returncode if returncode < 0 else returncode


def _forward_signal(processes: Sequence[subprocess.Popen[bytes]], signum: int) -> None:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signum)


def _stop_and_reap(processes: Sequence[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=_TERMINATE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=_KILL_TIMEOUT_SECONDS)


def main() -> int:
    """Start both local services and stop their sibling when either exits."""
    repo_root = Path(__file__).resolve().parents[1]
    api_port = Settings().api_port
    dashboard_environment = os.environ.copy()
    dashboard_environment[_DASHBOARD_API_PORT_ENV] = str(api_port)
    processes: list[subprocess.Popen[bytes]] = []
    received_signal: int | None = None

    def handle_signal(signum: int, _frame: FrameType | None) -> None:
        nonlocal received_signal
        if received_signal is None:
            received_signal = signum
        _forward_signal(processes, signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "argusfinance.api.app:app",
                    "--host",
                    _API_HOST,
                    "--port",
                    str(api_port),
                ],
                cwd=repo_root,
            )
        )
        if received_signal is not None:
            return 128 + received_signal
        processes.append(
            subprocess.Popen(
                [
                    "npm",
                    "--prefix",
                    str(repo_root / "apps" / "dashboard"),
                    "run",
                    "dev",
                    "--",
                    "--host",
                    _DASHBOARD_HOST,
                    "--port",
                    str(_DASHBOARD_PORT),
                    "--strictPort",
                ],
                cwd=repo_root,
                env=dashboard_environment,
            )
        )
        if received_signal is not None:
            return 128 + received_signal

        print(f"ArgusFinance API: http://{_API_HOST}:{api_port}", flush=True)
        print(
            f"ArgusFinance dashboard: http://{_DASHBOARD_HOST}:{_DASHBOARD_PORT}",
            flush=True,
        )

        while True:
            if received_signal is not None:
                return 128 + received_signal
            for process in processes:
                returncode = process.poll()
                if returncode is not None:
                    return _normalize_returncode(returncode)
            time.sleep(0.1)
    finally:
        _stop_and_reap(processes)


if __name__ == "__main__":
    raise SystemExit(main())
