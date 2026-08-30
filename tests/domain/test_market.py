from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from argusfinance.domain.market import (
    MarketDataStatus,
    MarketSnapshot,
    OptionQuote,
    UnderlyingQuote,
)


def test_underlying_quote_normalizes_ticker_and_preserves_provenance() -> None:
    observed = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    quote = UnderlyingQuote(
        ticker="nvda",
        price=Decimal("180.25"),
        source="mock",
        source_timestamp=observed,
        retrieved_at=observed,
        status=MarketDataStatus.REALTIME,
    )

    assert quote.ticker == "NVDA"
    assert quote.price == Decimal("180.25")
    assert quote.source_timestamp == observed
    assert quote.retrieved_at == observed
    assert quote.status is MarketDataStatus.REALTIME


def test_quote_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        UnderlyingQuote(
            ticker="NVDA",
            price=Decimal("180.25"),
            source="mock",
            source_timestamp=datetime.fromisoformat("2026-08-28T20:00:00"),
            retrieved_at=datetime.fromisoformat("2026-08-28T20:00:00"),
            status=MarketDataStatus.REALTIME,
        )


def test_market_values_are_immutable() -> None:
    observed = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)
    quote = UnderlyingQuote(
        ticker="NVDA",
        price=Decimal("180.25"),
        source="mock",
        source_timestamp=observed,
        retrieved_at=observed,
        status=MarketDataStatus.REALTIME,
    )
    option = _option_quote(observed)
    snapshot = MarketSnapshot(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000001"),
        underlying=quote,
        options=[option],
        created_at=observed,
    )

    with pytest.raises(ValidationError, match="frozen"):
        quote.ticker = "AAPL"  # type: ignore[misc]
    assert snapshot.options == (option,)


def test_option_quote_rejects_ask_below_bid() -> None:
    observed = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    with pytest.raises(ValidationError, match="ask must be greater than or equal to bid"):
        _option_quote(observed, bid=Decimal("4.00"), ask=Decimal("3.99"))


def _option_quote(
    observed: datetime,
    *,
    bid: Decimal = Decimal("3.95"),
    ask: Decimal = Decimal("4.05"),
) -> OptionQuote:
    return OptionQuote(
        ticker="NVDA",
        expiration=date(2026, 9, 18),
        strike=Decimal(180),
        option_type="CALL",
        bid=bid,
        ask=ask,
        volume=100,
        open_interest=1_000,
        implied_volatility=Decimal("0.45"),
        delta=Decimal("0.50"),
        gamma=Decimal("0.01"),
        theta=Decimal("-0.10"),
        vega=Decimal("0.20"),
        source="mock",
        source_timestamp=observed,
        retrieved_at=observed,
        status=MarketDataStatus.REALTIME,
    )
