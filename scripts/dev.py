"""Run the local API and dashboard together in the foreground."""

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


def _forward_signal(processes: Sequence[subprocess.Popen[bytes]], signum: int) -> None:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signum)


def _stop_and_reap(processes: Sequence[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait()


def main() -> int:
    """Start both local services and stop their sibling when either exits."""
    repo_root = Path(__file__).resolve().parents[1]
    api_port = Settings().api_port
    processes: list[subprocess.Popen[bytes]] = []

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
            )
        )

        def handle_signal(signum: int, _frame: FrameType | None) -> None:
            _forward_signal(processes, signum)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        print(f"ArgusFinance API: http://{_API_HOST}:{api_port}", flush=True)
        print(
            f"ArgusFinance dashboard: http://{_DASHBOARD_HOST}:{_DASHBOARD_PORT}",
            flush=True,
        )

        while True:
            for process in processes:
                returncode = process.poll()
                if returncode is not None:
                    return returncode
            time.sleep(0.1)
    finally:
        _stop_and_reap(processes)


if __name__ == "__main__":
    raise SystemExit(main())
