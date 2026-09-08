from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROSTER = {
    "company_analyst",
    "market_options_analyst",
    "historical_evidence_analyst",
    "strategy_analyst",
    "risk_critic",
    "optionstrat_operator",
}

_SPEC = importlib.util.spec_from_file_location(
    "validate_agent_roster", ROOT / "scripts" / "validate_agent_roster.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
validate_roster = _MODULE.validate_roster


def _copy_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    for relative_path in (".codex", ".codex-plugin", ".mcp.json", "skills", "agents"):
        source = ROOT / relative_path
        destination = project / relative_path
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return project


def test_project_defines_exact_approved_roster() -> None:
    assert validate_roster(ROOT) == EXPECTED_ROSTER


def test_role_paths_resolve_from_declaring_config_in_relocated_checkout(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    config_path = project / ".codex" / "config.toml"
    config = tomllib.loads(config_path.read_text())
    for role in EXPECTED_ROSTER:
        role_path = config_path.parent / config["agents"][role]["config_file"]
        assert role_path.is_file(), f"Codex cannot load {role} at {role_path}"
        assert tomllib.loads(role_path.read_text())["name"] == role


def test_validator_rejects_path_that_only_resolves_from_repo_root(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    config = project / ".codex" / "config.toml"
    config.write_text(config.read_text().replace(
        'config_file = "agents/', 'config_file = ".codex/agents/'
    ))
    with pytest.raises(ValueError, match="config.*path|config.*mapping"):
        validate_roster(project)


def test_install_agents_is_repeatable_and_validates_relocated_checkout(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    shutil.copy2(ROOT / "Makefile", project / "Makefile")
    shutil.copytree(ROOT / "scripts", project / "scripts")
    for _ in range(2):
        result = subprocess.run(
            ["make", "install-agents", f"PYTHON={sys.executable}"],
            cwd=project, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Validated roster:" in result.stdout
        assert (project / ".claude/skills/evaluate-ticker/SKILL.md").read_text() == (
            project / "skills/evaluate-ticker/SKILL.md"
        ).read_text()
    config = project / ".codex/config.toml"
    config.write_text(config.read_text().replace("company-analyst.toml", "missing.toml"))
    result = subprocess.run(
        ["make", "install-agents", f"PYTHON={sys.executable}"],
        cwd=project, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "config" in result.stderr


def test_rejects_an_extra_role_definition(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    (project / ".codex" / "agents" / "unapproved.toml").write_text(
        'name = "unapproved"\ndescription = "unapproved"\ndeveloper_instructions = "unapproved"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly"):
        validate_roster(project)


def test_rejects_risk_critique_before_strategy(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    skill = project / "skills" / "evaluate-ticker" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace(
            "After strategy output returns, dispatch `risk_critic`",
            "Dispatch `risk_critic` before strategy output returns",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="risk_critic"):
        validate_roster(project)


def test_rejects_operator_that_can_submit_a_paper_order(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    operator = project / ".codex" / "agents" / "optionstrat-operator.toml"
    operator.write_text(
        operator.read_text(encoding="utf-8").replace(
            "Never submits any live or paper order",
            "may submit a paper order",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="submit"):
        validate_roster(project)


def test_rejects_analytical_agent_granted_browser_authority(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    analyst = project / ".codex" / "agents" / "company-analyst.toml"
    analyst.write_text(
        analyst.read_text(encoding="utf-8").replace(
            "No browser, computer-use, database-write, or order authority.",
            "May use browser authority.",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden authority"):
        validate_roster(project)


def test_rejects_skill_that_allows_browser_invocation(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    skill = project / "skills" / "evaluate-ticker" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace(
            "the operator or browser",
            "the operator",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="browser"):
        validate_roster(project)


def test_rejects_skill_that_prefills_optionstrat(tmp_path: Path) -> None:
    project = _copy_project(tmp_path)
    skill = project / "skills" / "evaluate-ticker" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\nPrefill OptionStrat before returning the synthesis.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="browser"):
        validate_roster(project)


@pytest.mark.parametrize(
    "instruction",
    ["Call browser to prefill the trade.", "Invoke the operator to prepare the trade."],
)
def test_rejects_skill_with_other_browser_or_operator_action(tmp_path: Path, instruction: str) -> None:
    project = _copy_project(tmp_path)
    skill = project / "skills" / "evaluate-ticker" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + f"\n{instruction}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="browser|operator"):
        validate_roster(project)


@pytest.mark.parametrize("field", ["url", "env"])
def test_rejects_mcp_server_with_remote_or_secret_fields(tmp_path: Path, field: str) -> None:
    project = _copy_project(tmp_path)
    mcp = project / ".mcp.json"
    data = __import__("json").loads(mcp.read_text(encoding="utf-8"))
    data["mcpServers"]["argusfinance"][field] = "https://example.invalid" if field == "url" else {"TOKEN": "secret"}
    mcp.write_text(__import__("json").dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="MCP"):
        validate_roster(project)
