"""Normalization tests for saved connected-IBKR response bundles."""

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from argusfinance.adapters.ibkr_connector import normalize_ibkr_bundle
from argusfinance.domain.market import MarketDataStatus
from argusfinance.storage.snapshots import SnapshotStore


def _raw_bundle() -> dict[str, object]:
    return {
        "schema_version": 1,
        "ticker": "NVDA",
        "underlying": {
            "response": {
                "last": {"price": 226.06, "ts": 1788933498},
                "top-status": {"status": "REALTIME"},
            },
            "retrieved_at": "2026-09-09T06:00:01Z",
        },
        "options": [
            {
                "expiration": "2026-09-18",
                "strike": "225",
                "option_type": "CALL",
                "response": {
                    "last": {"price": 5.60, "ts": 1788933499},
                    "bid-ask": {"bid": 5.55, "ask": 5.65},
                    "top-status": {"status": "FROZEN_DELAYED"},
                    "option-midpoint-iv": {"annualIv": -15.874, "isValid": False},
                    "option-open-interest": {"callInterest": 46321, "putInterest": 991},
                    "volume": {"volume": 0},
                },
                "retrieved_at": "2026-09-09T06:00:02Z",
            },
            {
                "expiration": "2026-09-18",
                "strike": "225",
                "option_type": "PUT",
                "response": {
                    "bid-ask": {"bid": 4.40, "ask": 4.55, "ts": 1788933500},
                    "top-status": {"status": "SOMETHING_NEW"},
                    "option-midpoint-iv": {"annualIv": 42.5, "isValid": True},
                    "option-open-interest": {"callInterest": 999, "putInterest": 0},
                },
                "retrieved_at": "2026-09-09T06:00:03Z",
            },
        ],
        "notes": ["Sampled standard USD equity options; not the complete chain."],
    }


def test_normalizes_exact_raw_bundle_and_preserves_missing_evidence() -> None:
    snapshot = normalize_ibkr_bundle(_raw_bundle())

    call, put = snapshot.options
    assert snapshot.underlying.ticker == "NVDA"
    assert snapshot.underlying.price == Decimal("226.06")
    assert snapshot.underlying.source_timestamp == datetime.fromtimestamp(1788933498, UTC)
    assert snapshot.underlying.status is MarketDataStatus.REALTIME
    assert snapshot.created_at == datetime(2026, 9, 9, 6, 0, 3, tzinfo=UTC)
    assert call.source_timestamp is None
    assert call.implied_volatility is None
    assert call.open_interest == 46321
    assert call.volume == 0
    assert call.status is MarketDataStatus.FROZEN_DELAYED
    assert put.source_timestamp == datetime.fromtimestamp(1788933500, UTC)
    assert put.implied_volatility is None
    assert put.open_interest == 0
    assert put.volume is None
    assert put.status is MarketDataStatus.UNAVAILABLE
    assert snapshot.notes[0] == "Sampled standard USD equity options; not the complete chain."
    assert any("source timestamp" in note for note in snapshot.notes)
    assert any("implied volatility" in note for note in snapshot.notes)
    assert any("volume" in note for note in snapshot.notes)
    assert (
        "IBKR connector IV units are unspecified; implied volatility was not imported."
        in snapshot.notes
    )
    assert normalize_ibkr_bundle(_raw_bundle()).snapshot_id == snapshot.snapshot_id


def test_skips_missing_and_crossed_quotes_and_records_count() -> None:
    payload = _raw_bundle()
    options = payload["options"]
    assert isinstance(options, list)
    options.extend(
        [
            {
                "expiration": "2026-09-18",
                "strike": "230",
                "option_type": "CALL",
                "response": {"bid-ask": {"ask": 3.10}},
                "retrieved_at": "2026-09-09T06:00:04Z",
            },
            {
                "expiration": "2026-09-18",
                "strike": "230",
                "option_type": "PUT",
                "response": {"bid-ask": {"bid": 6.00, "ask": 5.90}},
                "retrieved_at": "2026-09-09T06:00:05Z",
            },
        ]
    )

    snapshot = normalize_ibkr_bundle(payload)

    assert len(snapshot.options) == 2
    assert any("Skipped 2 option quotes" in note for note in snapshot.notes)


def test_rejects_bundle_when_no_option_has_a_usable_quote() -> None:
    payload = _raw_bundle()
    options = payload["options"]
    assert isinstance(options, list)
    for option in options:
        assert isinstance(option, dict)
        option["response"] = {"bid-ask": {"bid": 6.00, "ask": 5.00}}

    with pytest.raises(ValueError, match="no usable option quotes"):
        normalize_ibkr_bundle(payload)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (("underlying", "last", "price", float("nan")), "underlying price"),
        (("underlying", "last", "ts", None), "underlying source timestamp"),
        (("underlying", "top-status", "status", None), "underlying status"),
        (("ticker", None, None, "../NVDA"), "ticker"),
    ],
)
def test_rejects_invalid_underlying_envelope(change: tuple[object, ...], message: str) -> None:
    payload = deepcopy(_raw_bundle())
    area, component, field, value = change
    if area == "ticker":
        payload["ticker"] = value
    else:
        underlying = payload["underlying"]
        assert isinstance(underlying, dict)
        response = underlying["response"]
        assert isinstance(response, dict)
        section = response[component]
        assert isinstance(section, dict)
        section[field] = value

    with pytest.raises(ValueError, match=message):
        normalize_ibkr_bundle(payload)


def test_rejects_expired_and_duplicate_option_identities() -> None:
    expired = _raw_bundle()
    options = expired["options"]
    assert isinstance(options, list)
    option = options[0]
    assert isinstance(option, dict)
    option["expiration"] = "2026-09-08"
    with pytest.raises(ValueError, match="expiration"):
        normalize_ibkr_bundle(expired)

    duplicate = _raw_bundle()
    duplicate_options = duplicate["options"]
    assert isinstance(duplicate_options, list)
    duplicate_options[1] = deepcopy(duplicate_options[0])
    with pytest.raises(ValueError, match="duplicate option identity"):
        normalize_ibkr_bundle(duplicate)


def test_same_day_option_expiration_is_allowed() -> None:
    payload = _raw_bundle()
    options = payload["options"]
    assert isinstance(options, list)
    for option in options:
        assert isinstance(option, dict)
        option["expiration"] = datetime.fromtimestamp(1788933498, UTC).date().isoformat()

    assert len(normalize_ibkr_bundle(payload).options) == 2


def test_rounds_binary_float_artifacts_to_explicit_parquet_money_scale() -> None:
    payload = _raw_bundle()
    underlying = payload["underlying"]
    assert isinstance(underlying, dict)
    response = underlying["response"]
    assert isinstance(response, dict)
    last = response["last"]
    assert isinstance(last, dict)
    last["price"] = 618.3000000000001
    options = payload["options"]
    assert isinstance(options, list)
    first = options[0]
    assert isinstance(first, dict)
    option_response = first["response"]
    assert isinstance(option_response, dict)
    bid_ask = option_response["bid-ask"]
    assert isinstance(bid_ask, dict)
    bid_ask["ask"] = 7.1000000000000005

    snapshot = normalize_ibkr_bundle(payload)

    assert snapshot.underlying.price == Decimal("618.3000000000")
    assert snapshot.options[0].ask == Decimal("7.1000000000")


def test_rounds_greek_artifacts_and_nulls_unrepresentable_values_before_storage(
    tmp_path: Path,
) -> None:
    payload = _raw_bundle()
    options = payload["options"]
    assert isinstance(options, list)
    first = options[0]
    assert isinstance(first, dict)
    response = first["response"]
    assert isinstance(response, dict)
    response["option-greeks"] = {
        "delta": 0.5000000000000001,
        "gamma": 0.0123456789014,
        "theta": -0.1234567890125,
        "vega": "1E+100",
    }

    snapshot = normalize_ibkr_bundle(payload)
    quote = snapshot.options[0]

    assert quote.delta == Decimal("0.500000000000")
    assert quote.gamma == Decimal("0.012345678901")
    assert quote.theta == Decimal("-0.123456789012")
    assert quote.vega is None
    store = SnapshotStore(tmp_path)
    store.write(snapshot)
    assert store.read(snapshot.snapshot_id) == snapshot
