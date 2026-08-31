# Task 9 report: fixed agent roster and local plugin shell

## Delivered files

- `.codex/config.toml` and six stable `.codex/agents/*.toml` definitions.
- `.codex-plugin/plugin.json` and local-only `.mcp.json` for `uv run argusfinance-mcp`.
- `skills/evaluate-ticker/SKILL.md`.
- Five role-memory files for each of the six roles under `agents/<role>/`.
- `scripts/validate_agent_roster.py` and mutation-oriented `tests/test_agent_roster.py`.

## TDD evidence

The first roster test run was RED because `scripts.validate_agent_roster` and the roster configuration did not yet exist. The completed focused suite is GREEN: five tests pass, including copied-tree mutations for an extra agent, early risk critique, paper-order authority, and analytical browser authority.

## Skill pressure RED baseline

Five fresh-context pressure runs without the skill skipped the historical role. Four ran risk before strategy; all five opened or prefilled OptionStrat early and promoted lessons directly to durable memory; three authorized paper-order submission. Recorded rationalizations were: "deadline dominates," "missing roles are non-blocking," "defined risk is enough," and "paper trade" as a lowered authority threshold.

The delivered skill directly requires all analytical lanes, stages strategy before risk, makes visual handoff explicit-only and operator-free, confines proposals to `pending.md`, and forbids live and paper orders.

## Validation

- `uv run pytest tests/test_agent_roster.py -v` — 5 passed.
- `uv run python scripts/validate_agent_roster.py` — exact six-role roster validated.
- `validate_plugin.py .` — passed.
- `quick_validate.py skills/evaluate-ticker` — passed.
- `uv run pytest -v` — 58 passed.
- `uv run ruff check src tests migrations scripts` — passed.
- `uv run mypy src/argusfinance` — passed.

Feature commit: `cdba158` (`feat: add fixed agent roster and plugin shell`).

## Skill GREEN forward validation

The controller completed five fresh-context repetitions of the identical pressure scenario. All five complied: snapshot first; all three evidence lanes including historical; strategy then risk dependency; failures marked rather than substituted; pending-only lessons; no early OptionStrat/browser; and no live or paper order placement, staging, or authorization. No new rationalizations or hybrid bypasses appeared, so no refactor was needed.

The plugin was not installed globally, no marketplace was modified, and no OptionStrat/browser action was invoked.

## Review round 1 validator hardening

Added copied-tree RED mutations for removing the skill's browser prohibition, injecting an OptionStrat prefill instruction, and adding either `url` or `env` to the local MCP server. All four initially failed because the validator did not reject them. The validator now requires the explicit no-browser sentence, rejects browser and OptionStrat prefill invocation language, and requires the local server object to contain exactly `command` and `args`. The mutations are GREEN; the focused roster suite reports 9 passed and the full suite reports 62 passed. Plugin validation, skill validation, Ruff, and mypy also remain GREEN.
