"""Service contracts joining immutable snapshots to exact payoff analysis."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.domain.market import MarketDataStatus, MarketSnapshot
from argusfinance.domain.strategy import (
    LegSide,
    OptionLeg,
    OptionType,
    Pricing,
    StrategyDraft,
    StrategyStatus,
)
from argusfinance.services.strategies import StrategyInputError, StrategyService


class SnapshotReader:
    """A real immutable fixture returned through the public read-by-ID boundary."""

    def __init__(self) -> None:
        self.snapshot = MockMarketDataProvider().get_snapshot("NVDA")

    def get(self, snapshot_id: UUID):
        assert snapshot_id == self.snapshot.snapshot_id
        return self.snapshot


def _draft(*, expiration: date = date(2026, 9, 18)) -> StrategyDraft:
    return StrategyDraft(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Research vertical",
        status=StrategyStatus.PAPER,
        pricing=Pricing.NATURAL,
        legs=(
            OptionLeg(expiration=expiration, strike=Decimal(175), option_type=OptionType.CALL, side=LegSide.BUY, quantity=1),
            OptionLeg(expiration=expiration, strike=Decimal(185), option_type=OptionType.CALL, side=LegSide.SELL, quantity=1),
        ),
    )


def test_evaluate_resolves_snapshot_quotes_and_identifies_frozen_evidence() -> None:
    """Changing natural bid/ask choice or omitting source warning must break this result."""
    result = StrategyService(SnapshotReader(), None).evaluate(_draft())

    assert result.net_debit == Decimal(505)
    assert result.maximum_profit == Decimal(495)
    assert result.net_greeks.delta == Decimal(22)
    assert result.eligible is True
    assert any("FROZEN" in warning for warning in result.warnings)


def test_evaluate_rejects_selected_contract_that_is_not_in_snapshot() -> None:
    """Returning an invented quote instead of a typed input error is invalid research output."""
    invalid = _draft()
    invalid = invalid.model_copy(update={"legs": (invalid.legs[0].model_copy(update={"strike": Decimal(190)}),)})

    with pytest.raises(StrategyInputError, match="not present"):
        StrategyService(SnapshotReader(), None).evaluate(invalid)


def test_rejects_contract_expired_at_snapshot_time() -> None:
    reader = SnapshotReader()
    payload = reader.snapshot.model_dump()
    for quote in payload["options"]:
        if quote["expiration"] == date(2026, 9, 18):
            quote["expiration"] = date(2026, 8, 27)
    reader.snapshot = MarketSnapshot.model_validate(payload)
    with pytest.raises(StrategyInputError, match="expired"):
        StrategyService(reader, None).evaluate(_draft(expiration=date(2026, 8, 27)))


@pytest.mark.parametrize("status,source,age,warning", [
    (MarketDataStatus.FROZEN, "ibkr", 0, "hypothetical"),
    (MarketDataStatus.REALTIME, "mock", 0, "hypothetical"),
    (MarketDataStatus.DELAYED, "ibkr", 48, "24-hour"),
])
def test_selected_quote_provenance_warns_even_with_fresh_underlying(status, source, age, warning, monkeypatch) -> None:
    reader = SnapshotReader()
    payload = reader.snapshot.model_dump()
    now = datetime(2026, 8, 28, tzinfo=UTC)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr("argusfinance.services.strategies.datetime", Clock)
    payload["underlying"].update(status=MarketDataStatus.REALTIME, source="ibkr", source_timestamp=now)
    for quote in payload["options"]:
        quote.update(status=MarketDataStatus.REALTIME, source="ibkr", source_timestamp=now)
        if quote["expiration"] == date(2026, 9, 18) and quote["strike"] == Decimal(175) and quote["option_type"] == "CALL":
            quote.update(status=status, source=source, source_timestamp=now - timedelta(hours=age))
    reader.snapshot = MarketSnapshot.model_validate(payload)
    evaluation = StrategyService(reader, None).evaluate(_draft())
    assert any(warning in item for item in evaluation.warnings)


def test_selected_imported_quote_warns_for_frozen_delayed_and_missing_fields() -> None:
    reader = SnapshotReader()
    payload = reader.snapshot.model_dump()
    for quote in payload["options"]:
        if quote["expiration"] == date(2026, 9, 18):
            quote.update(
                status=MarketDataStatus.FROZEN_DELAYED,
                source="ibkr",
                source_timestamp=None,
                implied_volatility=None,
                open_interest=None,
                volume=None,
            )
    reader.snapshot = MarketSnapshot.model_validate(payload)

    evaluation = StrategyService(reader, None).evaluate(_draft())

    assert any("FROZEN_DELAYED" in warning for warning in evaluation.warnings)
    assert any("source timestamp" in warning for warning in evaluation.warnings)
    assert any("implied volatility" in warning for warning in evaluation.warnings)
