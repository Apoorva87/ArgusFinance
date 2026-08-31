"""Validate ArgusFinance's fixed, non-trading research-agent roster."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ANALYTICAL_ROLES = {
    "company_analyst",
    "market_options_analyst",
    "historical_evidence_analyst",
    "strategy_analyst",
    "risk_critic",
}
OPERATOR = "optionstrat_operator"
EXPECTED_ROSTER = ANALYTICAL_ROLES | {OPERATOR}
ROLE_FILES = {role: role.replace("_", "-") + ".toml" for role in EXPECTED_ROSTER}
MEMORY_FILES = (
    "PLAYBOOK.md",
    "CHECKLIST.md",
    "SOURCES.md",
    "lessons/pending.md",
    "lessons/approved.md",
)
LESSON_HEADINGS = ("## Date", "## Evaluation ID", "## Evidence/Source IDs", "## Proposed Lesson", "## Scope", "## Reviewer/Status")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_text(path: Path) -> str:
    _require(path.is_file(), f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _validate_agent(role: str, path: Path) -> None:
    data = tomllib.loads(_read_text(path))
    _require(data.get("name") == role, f"agent name mismatch: {path}")
    instructions = str(data.get("developer_instructions", "")).lower()
    _require(bool(data.get("description")), f"agent description missing: {role}")
    _require(bool(instructions), f"agent instructions missing: {role}")
    if role in ANALYTICAL_ROLES:
        _require(data.get("sandbox_mode") == "read-only", f"analytical agent must be read-only: {role}")
        forbidden_grants = (
            "may use browser",
            "can use browser",
            "browser authority",
            "may use computer-use",
            "may submit",
            "may place",
            "may write to database",
            "database-write permission",
        )
        _require(not any(grant in instructions for grant in forbidden_grants), f"analytical agent has forbidden authority: {role}")
        _require("approved.md" in instructions, f"analytical agent must read approved lessons: {role}")
    else:
        for rule in ("explicit-only", "typed handoff", "verify every leg", "user-takeover", "never submits any live or paper order"):
            _require(rule in instructions, f"operator missing safety rule {rule!r}")
        _require(not any(grant in instructions for grant in ("may write to database", "database-write permission")), "operator must not have database-write authority")


def _validate_memory(root: Path, role: str) -> None:
    role_root = root / "agents" / role
    _require(role_root.is_dir(), f"missing role directory: {role}")
    _require({path.name for path in role_root.iterdir()} == {"PLAYBOOK.md", "CHECKLIST.md", "SOURCES.md", "lessons"}, f"role directory has unexpected files: {role}")
    _require({path.name for path in (role_root / "lessons").iterdir()} == {"pending.md", "approved.md"}, f"lesson directory has unexpected files: {role}")
    for relative_path in MEMORY_FILES:
        content = _read_text(role_root / relative_path)
        if relative_path.startswith("lessons/"):
            _require(all(heading in content for heading in LESSON_HEADINGS), f"lesson schema headings missing: {role}/{relative_path}")
    playbook = _read_text(role_root / "PLAYBOOK.md").lower()
    _require(all(heading in playbook for heading in ("## scope", "## required inputs", "## output contract", "## failure states", "## non-responsibilities")), f"playbook sections missing: {role}")


def _validate_plugin(root: Path) -> None:
    plugin = json.loads(_read_text(root / ".codex-plugin" / "plugin.json"))
    _require(plugin.get("name") == "argusfinance" and plugin.get("version") == "0.1.0", "invalid plugin identity")
    _require(plugin.get("skills") == "./skills/" and plugin.get("mcpServers") == "./.mcp.json", "invalid plugin linkage")
    _require(plugin.get("author", {}).get("name") == "Apoorva Karnik", "invalid plugin author")
    mcp = json.loads(_read_text(root / ".mcp.json"))
    _require(set(mcp.get("mcpServers", {})) == {"argusfinance"}, "invalid local MCP server set")
    server = mcp["mcpServers"]["argusfinance"]
    _require(set(server) == {"command", "args"}, "invalid local MCP server shape")
    _require(server.get("command") == "uv" and server.get("args") == ["run", "argusfinance-mcp"], "wrong local MCP command")


def _validate_skill(root: Path) -> None:
    skill = _read_text(root / "skills" / "evaluate-ticker" / "SKILL.md")
    lower = skill.lower()
    _require(skill.startswith("---\nname: evaluate-ticker\ndescription: Use when"), "invalid skill frontmatter")
    handoff_line = (
        "6. Only when the user explicitly asks for visual handoff, return a typed "
        "`optionstrat_handoff` packet. This skill never invokes the operator or browser."
    )
    pressure_line = "| Sunk work justifies early OptionStrat | No handoff until explicit user request after synthesis. |"
    _require(handoff_line in skill.splitlines(), "skill must prohibit browser and operator invocation")
    _require(
        all(
            line in {handoff_line, pressure_line}
            for line in skill.splitlines()
            if any(term in line.lower() for term in ("browser", "optionstrat", "operator"))
        ),
        "skill has an unauthorized browser, OptionStrat, or operator reference",
    )
    _require(all(role in lower for role in ANALYTICAL_ROLES), "skill lacks an analytical role")
    fanout = lower.index("company_analyst")
    strategy = lower.index("strategy_analyst")
    risk = lower.index("risk_critic")
    _require(fanout < strategy < risk and "after strategy output returns, dispatch `risk_critic`" in lower, "risk_critic must run after strategy")
    _require("pending.md" in lower and "only" in lower and "never promote" in lower, "skill may auto-promote approved memory")
    _require("never place, stage, submit, or authorize live or paper orders" in lower, "skill permits paper/live orders")
    _require("capture_market_snapshot" in skill and "insufficient_data" in skill, "skill lacks snapshot failure boundary")


def validate_roster(root: Path) -> set[str]:
    """Return the exact roster after validating every required safety boundary."""
    config = tomllib.loads(_read_text(root / ".codex" / "config.toml"))
    agents = config.get("agents", {})
    _require(agents.get("enabled") is True and agents.get("max_concurrent_threads_per_session") == 5, "agent concurrency must be five")
    _require(set(agents) - {"enabled", "max_concurrent_threads_per_session"} == EXPECTED_ROSTER, "config must define exactly the approved roster")
    agent_dir = root / ".codex" / "agents"
    _require({path.name for path in agent_dir.glob("*.toml")} == set(ROLE_FILES.values()), "agent files must define exactly the approved roster")
    for role, filename in ROLE_FILES.items():
        _require(agents[role].get("config_file") == f".codex/agents/{filename}", f"agent config mapping invalid: {role}")
        _validate_agent(role, agent_dir / filename)
        _validate_memory(root, role)
    _validate_plugin(root)
    _validate_skill(root)
    return EXPECTED_ROSTER


if __name__ == "__main__":
    roster = validate_roster(Path("."))
    print("Validated roster: " + ", ".join(sorted(roster)))
