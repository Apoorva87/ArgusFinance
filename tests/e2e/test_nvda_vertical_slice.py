"""End-to-end proof for the persisted NVDA market snapshot."""

import importlib
import importlib.util
import json
import shutil
import signal
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from argusfinance.bootstrap import build_container
from argusfinance.cli import app as cli_app
from argusfinance.config import Settings, get_settings
from argusfinance.mcp_server import MarketMcpTools

JsonObject = dict[str, Any]


def _load_dev_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "dev.py"
    spec = importlib.util.spec_from_file_location("argusfinance_dev", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolved_vite_api_proxy(api_port: str | None = None) -> JsonObject:
    dashboard_root = Path(__file__).resolve().parents[2] / "apps" / "dashboard"
    node = shutil.which("node")
    assert node is not None
    environment = {} if api_port is None else {"ARGUS_DASHBOARD_API_PORT": api_port}
    result = subprocess.run(
        [
            node,
            "--input-type=module",
            "-e",
            (
                "const {loadConfigFromFile} = await import('vite');"
                "const loaded = await loadConfigFromFile("
                "{command:'serve',mode:'development'},'./vite.config.ts');"
                "console.log(JSON.stringify(loaded.config.server?.proxy?.['/api'] ?? null));"
            ),
        ],
        cwd=dashboard_root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@dataclass(frozen=True)
class VerticalSlice:
    """Exercise each public boundary against one local persisted state."""

    client: TestClient
    cli_runner: CliRunner
    mcp_tools: MarketMcpTools

    def capture_with_api(self, ticker: str, weeks: int) -> JsonObject:
        response = self.client.post(
            f"/api/market/{ticker}/snapshots",
            params={"weeks": weeks},
        )
        assert response.status_code == 201
        return response.json()

    def latest_with_cli(self, ticker: str) -> JsonObject:
        result = self.cli_runner.invoke(cli_app, ["market", "latest", ticker])
        assert result.exit_code == 0
        return json.loads(result.stdout)

    def latest_with_mcp(self, ticker: str) -> JsonObject:
        return self.mcp_tools.get_latest_market_snapshot(ticker)


@pytest.fixture
def vertical_slice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    apply_migrations: Callable[[str], None],
) -> Iterator[VerticalSlice]:
    state_dir = tmp_path / "state"
    database_url = f"sqlite:///{tmp_path / 'workspace.sqlite'}"
    monkeypatch.setenv("ARGUS_STATE_DIR", str(state_dir))
    monkeypatch.setenv("ARGUS_DATABASE_URL", database_url)
    apply_migrations(database_url)

    settings = Settings(state_dir=state_dir, database_url=database_url)
    container = build_container(settings)

    # Import only after the temporary environment is installed: the module's
    # development ASGI app is composed at import time.
    get_settings.cache_clear()
    api_module = importlib.import_module("argusfinance.api.app")
    app = api_module.create_app(settings, container)
    with TestClient(app) as client:
        yield VerticalSlice(
            client=client,
            cli_runner=CliRunner(),
            mcp_tools=MarketMcpTools(container.market_service),
        )
    get_settings.cache_clear()


def test_nvda_snapshot_identity_across_api_cli_and_mcp(vertical_slice):
    api_snapshot = vertical_slice.capture_with_api("NVDA", weeks=8)
    cli_snapshot = vertical_slice.latest_with_cli("NVDA")
    mcp_snapshot = vertical_slice.latest_with_mcp("NVDA")

    assert api_snapshot["snapshot_id"] == cli_snapshot["snapshot_id"]
    assert api_snapshot["snapshot_id"] == mcp_snapshot["snapshot_id"]
    assert api_snapshot["underlying"]["ticker"] == "NVDA"


def test_dashboard_dev_server_proxies_api_to_exact_local_backend() -> None:
    assert _resolved_vite_api_proxy() == {"target": "http://127.0.0.1:8765"}


def test_dashboard_dev_server_proxies_api_to_resolved_non_default_port() -> None:
    assert _resolved_vite_api_proxy("9123") == {"target": "http://127.0.0.1:9123"}


@pytest.mark.parametrize("unsafe_port", ["", "0", "65536", "9123/path"])
def test_dashboard_dev_server_rejects_unsafe_proxy_port(unsafe_port: str) -> None:
    assert _resolved_vite_api_proxy(unsafe_port) == {"target": "http://127.0.0.1:8765"}


def test_launcher_starts_local_children_and_terminates_surviving_sibling(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dev = _load_dev_module()
    repo_root = Path(__file__).resolve().parents[2]

    class FakeProcess:
        def __init__(self, name: str, returncode: int | None) -> None:
            self.name = name
            self.returncode = returncode
            self.terminated = False
            self.waited = False

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = -signal.SIGTERM

        def wait(self, timeout: float | None = None) -> int:
            self.waited = True
            assert timeout is not None
            assert self.returncode is not None
            return self.returncode

        def send_signal(self, signum: int) -> None:
            self.returncode = -signum

    api = FakeProcess("api", 7)
    dashboard = FakeProcess("dashboard", None)
    processes = iter((api, dashboard))
    popen_calls: list[tuple[list[str], Path]] = []
    dashboard_api_ports: list[str] = []

    def fake_popen(
        command: list[str],
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> FakeProcess:
        popen_calls.append((command, cwd))
        if env is not None:
            dashboard_api_ports.append(env["ARGUS_DASHBOARD_API_PORT"])
        return next(processes)

    monkeypatch.setattr(dev.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(dev.signal, "signal", lambda *_args: None)

    assert dev.main() == 7
    assert popen_calls == [
        (
            [
                dev.sys.executable,
                "-m",
                "uvicorn",
                "argusfinance.api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
            ],
            repo_root,
        ),
        (
            [
                "npm",
                "--prefix",
                str(repo_root / "apps" / "dashboard"),
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                "5173",
                "--strictPort",
            ],
            repo_root,
        ),
    ]
    assert capsys.readouterr().out.splitlines() == [
        "ArgusFinance API: http://127.0.0.1:8765",
        "ArgusFinance dashboard: http://127.0.0.1:5173",
    ]
    assert not api.terminated
    assert dashboard.terminated
    assert api.waited and dashboard.waited
    assert dashboard_api_ports == ["8765"]


def test_launcher_forwards_termination_signals_to_both_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dev = _load_dev_module()
    handlers: dict[int, Any] = {}

    class SignalAwareProcess:
        def __init__(self, trigger_signal: bool) -> None:
            self.trigger_signal = trigger_signal
            self.returncode: int | None = None
            self.received: list[int] = []

        def poll(self) -> int | None:
            if self.trigger_signal and self.returncode is None:
                self.trigger_signal = False
                handlers[signal.SIGINT](signal.SIGINT, None)
            return self.returncode

        def send_signal(self, signum: int) -> None:
            self.received.append(signum)
            self.returncode = -signum

        def terminate(self) -> None:
            self.returncode = -signal.SIGTERM

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is not None
            assert self.returncode is not None
            return self.returncode

    api = SignalAwareProcess(trigger_signal=True)
    dashboard = SignalAwareProcess(trigger_signal=False)
    processes = iter((api, dashboard))
    monkeypatch.setattr(dev.subprocess, "Popen", lambda *_args, **_kwargs: next(processes))
    monkeypatch.setattr(dev.signal, "signal", handlers.__setitem__)

    assert dev.main() == 128 + signal.SIGINT
    assert set(handlers) == {signal.SIGINT, signal.SIGTERM}
    assert api.received == [signal.SIGINT]
    assert dashboard.received == [signal.SIGINT]


def test_launcher_installs_handlers_before_startup_and_stops_after_startup_signal(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dev = _load_dev_module()
    handlers: dict[int, Any] = {}

    class StartupProcess:
        def __init__(self) -> None:
            self.returncode: int | None = None
            self.terminated = False
            self.waited = False

        def poll(self) -> int | None:
            return self.returncode

        def send_signal(self, signum: int) -> None:
            self.returncode = -signum

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = -signal.SIGTERM

        def wait(self, timeout: float | None = None) -> int:
            self.waited = True
            assert timeout is not None
            assert self.returncode is not None
            return self.returncode

    api = StartupProcess()
    popen_calls = 0

    def interrupting_popen(*_args: object, **_kwargs: object) -> StartupProcess:
        nonlocal popen_calls
        popen_calls += 1
        assert set(handlers) == {signal.SIGINT, signal.SIGTERM}
        assert popen_calls == 1, "dashboard must not start after startup interruption"
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        return api

    monkeypatch.setattr(dev.signal, "signal", handlers.__setitem__)
    monkeypatch.setattr(dev.subprocess, "Popen", interrupting_popen)

    assert dev.main() == 128 + signal.SIGTERM
    assert popen_calls == 1
    assert api.terminated and api.waited
    assert capsys.readouterr().out == ""


def test_launcher_kills_and_reaps_first_child_when_dashboard_startup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dev = _load_dev_module()

    class NonCooperativeProcess:
        def __init__(self) -> None:
            self.returncode: int | None = None
            self.terminated = False
            self.killed = False
            self.wait_timeouts: list[float | None] = []

        def poll(self) -> int | None:
            return self.returncode

        def send_signal(self, _signum: int) -> None:
            pass

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True
            self.returncode = -signal.SIGKILL

        def wait(self, timeout: float | None = None) -> int:
            self.wait_timeouts.append(timeout)
            assert timeout is not None, "launcher cleanup waits must be bounded"
            if self.returncode is None:
                raise subprocess.TimeoutExpired("api", timeout)
            return self.returncode

    api = NonCooperativeProcess()
    popen_calls = 0

    def failing_popen(*_args: object, **_kwargs: object) -> NonCooperativeProcess:
        nonlocal popen_calls
        popen_calls += 1
        if popen_calls == 1:
            return api
        raise OSError("npm unavailable")

    monkeypatch.setattr(dev.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(dev.subprocess, "Popen", failing_popen)

    with pytest.raises(OSError, match="^npm unavailable$"):
        dev.main()

    assert popen_calls == 2
    assert api.terminated and api.killed
    assert len(api.wait_timeouts) == 2
    assert all(timeout is not None for timeout in api.wait_timeouts)


def test_launcher_passes_resolved_api_port_to_dashboard_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARGUS_API_PORT", "9123")
    dev = _load_dev_module()

    class ConfiguredProcess:
        def __init__(self, returncode: int | None) -> None:
            self.returncode = returncode

        def poll(self) -> int | None:
            return self.returncode

        def send_signal(self, signum: int) -> None:
            self.returncode = -signum

        def terminate(self) -> None:
            self.returncode = -signal.SIGTERM

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is not None
            assert self.returncode is not None
            return self.returncode

    processes = iter((ConfiguredProcess(0), ConfiguredProcess(None)))
    popen_calls: list[tuple[list[str], dict[str, str] | None]] = []

    def recording_popen(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> ConfiguredProcess:
        assert cwd == Path(__file__).resolve().parents[2]
        popen_calls.append((command, env))
        return next(processes)

    monkeypatch.setattr(dev.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(dev.subprocess, "Popen", recording_popen)

    assert dev.main() == 0
    assert popen_calls[0][0][-1] == "9123"
    dashboard_environment = popen_calls[1][1]
    assert dashboard_environment is not None
    assert dashboard_environment["ARGUS_DASHBOARD_API_PORT"] == "9123"
