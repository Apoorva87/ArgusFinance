"""Snapshot-backed strategy evaluation and save workflow."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from argusfinance.analytics.payoff import evaluate_expiration_payoff
from argusfinance.domain.market import (
    MarketDataStatus,
    MarketSnapshot,
    OptionQuote,
    UnderlyingQuote,
)
from argusfinance.domain.strategy import (
    LegSide,
    Pricing,
    SavedStrategy,
    StrategyDraft,
    StrategyEvaluation,
)


class StrategyInputError(ValueError):
    """Raised for structurally invalid selections against otherwise known evidence."""


class StrategySnapshotNotFoundError(LookupError):
    """Raised when a draft references absent immutable market evidence."""


class StrategyNotFoundError(LookupError):
    """Raised when a saved research document cannot be read."""


class SnapshotReader(Protocol):
    def get(self, snapshot_id: str | UUID) -> MarketSnapshot: ...


class StrategyRepository(Protocol):
    def save(self, saved: SavedStrategy) -> None: ...

    def list(self) -> list[SavedStrategy]: ...

    def get(self, strategy_id: UUID) -> SavedStrategy | None: ...


class StrategyService:
    """Evaluate only selected immutable snapshot quotes, then save atomically."""

    def __init__(self, market_service: SnapshotReader, repository: StrategyRepository | None) -> None:
        self._market_service = market_service
        self._repository = repository

    def evaluate(self, draft: StrategyDraft) -> StrategyEvaluation:
        """Resolve draft legs from one snapshot and calculate its exact expiry payoff."""
        try:
            snapshot = self._market_service.get(draft.snapshot_id)
        except LookupError as error:
            raise StrategySnapshotNotFoundError("Market snapshot was not found") from error
        self._validate_snapshot(snapshot)
        resolved = []
        selected_quotes = []
        expirations = {leg.expiration for leg in draft.legs}
        if len(expirations) != 1:
            raise StrategyInputError("selected option legs must share one expiration")
        for leg in draft.legs:
            if leg.expiration < snapshot.underlying.source_timestamp.date():
                raise StrategyInputError("selected option contract was expired at the snapshot timestamp")
            quote = _find_option(snapshot, leg.expiration, leg.strike, leg.option_type.value)
            if quote is None:
                raise StrategyInputError("selected option contract is not present in the snapshot")
            if quote.status is MarketDataStatus.UNAVAILABLE:
                raise StrategyInputError("selected option quote is UNAVAILABLE")
            premium = _premium(quote, leg.side, draft.pricing)
            selected_quotes.append(quote)
            resolved.append((leg, premium, quote.delta, quote.gamma, quote.theta, quote.vega))
        analysis = evaluate_expiration_payoff(draft, resolved, snapshot.underlying.price)
        warnings = [*analysis.warnings, *_warnings(snapshot, selected_quotes)]
        return StrategyEvaluation(
            snapshot_id=snapshot.snapshot_id,
            ticker=snapshot.underlying.ticker,
            expiration=next(iter(expirations)),
            spot=snapshot.underlying.price,
            pricing=draft.pricing,
            legs=analysis.legs,
            net_debit=analysis.net_debit,
            entry_fees=analysis.entry_fees,
            maximum_profit=analysis.maximum_profit,
            maximum_loss=analysis.maximum_loss,
            breakevens=analysis.breakevens,
            payoff_points=analysis.payoff_points,
            net_greeks=analysis.net_greeks,
            warnings=warnings,
            eligible=True,
            analytics_version="expiration-payoff-v1",
            source_timestamp=snapshot.underlying.source_timestamp,
            source_status=snapshot.underlying.status,
            boundaries=draft.boundaries,
        )

    def save(self, draft: StrategyDraft) -> SavedStrategy:
        """Evaluate once and atomically retain the immutable entry document."""
        if self._repository is None:
            raise RuntimeError("strategy persistence is not configured")
        saved = SavedStrategy(
            id=uuid4(),
            created_at=datetime.now(UTC),
            draft=draft,
            evaluation=self.evaluate(draft),
        )
        self._repository.save(saved)
        return saved

    def list(self) -> list[SavedStrategy]:
        """List saved documents newest first."""
        if self._repository is None:
            raise RuntimeError("strategy persistence is not configured")
        return self._repository.list()

    def get(self, strategy_id: UUID) -> SavedStrategy:
        """Read a saved immutable evaluation without resolving live market data."""
        if self._repository is None:
            raise RuntimeError("strategy persistence is not configured")
        saved = self._repository.get(strategy_id)
        if saved is None:
            raise StrategyNotFoundError("Saved strategy was not found")
        return saved

    @staticmethod
    def _validate_snapshot(snapshot: MarketSnapshot) -> None:
        if snapshot.underlying.status is MarketDataStatus.UNAVAILABLE:
            raise StrategyInputError("underlying quote is UNAVAILABLE")


def _find_option(
    snapshot: MarketSnapshot, expiration: date, strike: Decimal, option_type: str
) -> OptionQuote | None:
    for quote in snapshot.options:
        if quote.expiration == expiration and quote.strike == strike and quote.option_type == option_type:
            return quote
    return None


def _premium(quote: OptionQuote, side: LegSide, pricing: Pricing) -> Decimal:
    if pricing is Pricing.MIDPOINT:
        return (quote.bid + quote.ask) / Decimal(2)
    return quote.ask if side is LegSide.BUY else quote.bid


def _warnings(snapshot: MarketSnapshot, selected_quotes: list[OptionQuote]) -> list[str]:
    warnings: list[str] = []
    evidence: list[UnderlyingQuote | OptionQuote] = [snapshot.underlying, *selected_quotes]
    if any(
        quote.status in {MarketDataStatus.FROZEN, MarketDataStatus.FROZEN_DELAYED}
        or quote.source == "mock"
        for quote in evidence
    ):
        warnings.append(
            "FROZEN/FROZEN_DELAYED/mock snapshot: hypothetical analysis, not live market evidence"
        )
    if any(quote.status in {MarketDataStatus.DELAYED, MarketDataStatus.FROZEN_DELAYED} for quote in evidence):
        warnings.append("Selected evidence includes a DELAYED or FROZEN_DELAYED quote")
    if any(quote.source_timestamp is None for quote in selected_quotes):
        warnings.append("Selected option evidence has no bid/ask source timestamp")
    if any(quote.implied_volatility is None for quote in selected_quotes):
        warnings.append("Selected option evidence has unavailable implied volatility")
    if any(quote.open_interest is None for quote in selected_quotes):
        warnings.append("Selected option evidence has unavailable open interest")
    if any(quote.volume is None for quote in selected_quotes):
        warnings.append("Selected option evidence has unavailable volume")
    now = datetime.now(UTC)
    if any(
        quote.status in {MarketDataStatus.REALTIME, MarketDataStatus.DELAYED}
        and quote.source_timestamp is not None
        and (now - quote.source_timestamp).total_seconds() > 86400
        for quote in evidence
    ):
        warnings.append("Source timestamp is older than the documented 24-hour staleness policy")
    return warnings
