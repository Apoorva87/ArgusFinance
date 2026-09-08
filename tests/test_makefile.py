"""Tests for the local Makefile runtime command contract."""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_make_run_resolves_api_port_through_settings() -> None:
    environment = os.environ.copy()
    environment.pop("ARGUS_API_PORT", None)
    result = subprocess.run(
        ["make", "-n", "run"],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Settings().api_port" in result.stdout
    assert "--port $(ARGUS_API_PORT)" not in result.stdout
