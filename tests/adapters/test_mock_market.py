from datetime import UTC, datetime

import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.domain.market import MarketDataStatus


def test_mock_provider_returns_eight_week_nvda_fixture() -> None:
    snapshot = MockMarketDataProvider().get_snapshot("NVDA", weeks=8)

    assert snapshot.underlying.ticker == "NVDA"
    assert len(snapshot.options) == 8
    assert {quote.option_type for quote in snapshot.options} == {"CALL", "PUT"}
    assert len({quote.expiration for quote in snapshot.options}) == 2


def test_mock_provider_rejects_unsupported_ticker() -> None:
    with pytest.raises(ValueError, match="Mock provider supports only NVDA"):
        MockMarketDataProvider().get_snapshot("AAPL")


def test_mock_provider_returns_equal_fixed_snapshot_on_repeated_calls() -> None:
    provider = MockMarketDataProvider()

    first = provider.get_snapshot("nvda")
    second = provider.get_snapshot("NVDA")

    assert first == second
    assert first.created_at == datetime(2026, 8, 28, 20, 0, tzinfo=UTC)
    assert first.underlying.source == "mock"
    assert first.underlying.source_timestamp == first.created_at
    assert first.underlying.retrieved_at == first.created_at
    assert first.underlying.status is MarketDataStatus.FROZEN
    assert {option.source_timestamp for option in first.options} == {first.created_at}
    assert {option.retrieved_at for option in first.options} == {first.created_at}


def test_mock_provider_reports_deterministic_diagnostic() -> None:
    assert MockMarketDataProvider().diagnostic() == {
        "provider": "mock",
        "connected": True,
        "mode": "deterministic",
    }


def test_mock_provider_rejects_unsupported_horizon() -> None:
    with pytest.raises(ValueError, match="supports only weeks=8"):
        MockMarketDataProvider().get_snapshot("NVDA", weeks=4)
