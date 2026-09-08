"""Local command-line entry points for ArgusFinance."""

import json
from pathlib import Path
from uuid import UUID

import typer

from argusfinance.adapters.ibkr import IbkrMarketDataProvider
from argusfinance.bootstrap import build_container
from argusfinance.config import Settings
from argusfinance.domain.strategy import StrategyDraft
from argusfinance.services.market import (
    LatestSnapshotNotFoundError,
    MarketService,
    ProviderInputError,
)
from argusfinance.services.strategies import (
    StrategyInputError,
    StrategyNotFoundError,
    StrategyService,
    StrategySnapshotNotFoundError,
)

app = typer.Typer(no_args_is_help=True)
market_app = typer.Typer(no_args_is_help=True)
provider_app = typer.Typer(no_args_is_help=True)
diagnostic_app = typer.Typer(no_args_is_help=True)
strategy_app = typer.Typer(no_args_is_help=True)

app.add_typer(market_app, name="market")
app.add_typer(provider_app, name="provider")
app.add_typer(strategy_app, name="strategy")
provider_app.add_typer(diagnostic_app, name="diagnostic")


def _market_service() -> MarketService:
    """Build fresh local settings for each independent CLI invocation."""
    return build_container(Settings()).market_service


def _strategy_service() -> StrategyService:
    """Build the shared snapshot-backed strategy workflow for one CLI command."""
    return build_container(Settings()).strategy_service


def _read_draft(path: Path) -> StrategyDraft:
    try:
        return StrategyDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="<json-file>") from error


def _strategy_error(error: Exception) -> None:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=1) from error


@market_app.command("snapshot")
def market_snapshot(ticker: str, weeks: int = 8) -> None:
    """Capture and persist a market snapshot."""
    try:
        snapshot = _market_service().capture(ticker, weeks)
    except ProviderInputError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(snapshot.model_dump_json(indent=2))


@market_app.command("latest")
def market_latest(ticker: str) -> None:
    """Read the newest persisted market snapshot."""
    try:
        snapshot = _market_service().latest(ticker)
    except LatestSnapshotNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(snapshot.model_dump_json(indent=2))


@strategy_app.command("evaluate")
def strategy_evaluate(draft_path: Path) -> None:
    """Evaluate a JSON strategy draft against its saved snapshot."""
    try:
        evaluation = _strategy_service().evaluate(_read_draft(draft_path))
    except (StrategyInputError, StrategySnapshotNotFoundError) as error:
        _strategy_error(error)
    typer.echo(evaluation.model_dump_json(indent=2))


@strategy_app.command("save")
def strategy_save(draft_path: Path) -> None:
    """Save a JSON draft and its immutable entry evaluation."""
    try:
        saved = _strategy_service().save(_read_draft(draft_path))
    except (StrategyInputError, StrategySnapshotNotFoundError) as error:
        _strategy_error(error)
    typer.echo(saved.model_dump_json(indent=2))


@strategy_app.command("list")
def strategy_list() -> None:
    """List saved strategy documents newest first."""
    typer.echo(json.dumps([saved.model_dump(mode="json") for saved in _strategy_service().list()], indent=2))


@strategy_app.command("get")
def strategy_get(strategy_id: UUID) -> None:
    """Read one saved strategy document by UUID."""
    try:
        saved = _strategy_service().get(strategy_id)
    except StrategyNotFoundError as error:
        _strategy_error(error)
    typer.echo(saved.model_dump_json(indent=2))


@diagnostic_app.command("ibkr")
def ibkr_diagnostic() -> None:
    """Run the narrow, read-only Interactive Brokers connectivity diagnostic."""
    typer.echo(json.dumps(IbkrMarketDataProvider().diagnostic(), indent=2))
