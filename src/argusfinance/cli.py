"""Local command-line entry points for ArgusFinance."""

import json

import typer

from argusfinance.adapters.ibkr import IbkrMarketDataProvider
from argusfinance.bootstrap import build_container
from argusfinance.config import Settings
from argusfinance.services.market import (
    LatestSnapshotNotFoundError,
    MarketService,
    ProviderInputError,
)

app = typer.Typer(no_args_is_help=True)
market_app = typer.Typer(no_args_is_help=True)
provider_app = typer.Typer(no_args_is_help=True)
diagnostic_app = typer.Typer(no_args_is_help=True)

app.add_typer(market_app, name="market")
app.add_typer(provider_app, name="provider")
provider_app.add_typer(diagnostic_app, name="diagnostic")


def _market_service() -> MarketService:
    """Build fresh local settings for each independent CLI invocation."""
    return build_container(Settings()).market_service


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


@diagnostic_app.command("ibkr")
def ibkr_diagnostic() -> None:
    """Run the narrow, read-only Interactive Brokers connectivity diagnostic."""
    typer.echo(json.dumps(IbkrMarketDataProvider().diagnostic(), indent=2))
