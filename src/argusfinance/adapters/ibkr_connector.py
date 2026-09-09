"""Normalize saved connected-IBKR responses into shared market snapshots."""

import json
import math
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Literal, cast
from uuid import UUID, uuid5

from argusfinance.domain.market import (
    MarketDataStatus,
    MarketSnapshot,
    OptionQuote,
    UnderlyingQuote,
)

_BUNDLE_NAMESPACE = UUID("b9a83612-c801-43c0-b72f-cee04377c9f9")
_TOP_LEVEL_KEYS = {"schema_version", "ticker", "underlying", "options", "notes"}
_UNDERLYING_KEYS = {"response", "retrieved_at"}
_OPTION_KEYS = {
    "expiration",
    "strike",
    "option_type",
    "response",
    "retrieved_at",
}
_MONEY_QUANTUM = Decimal("0.0000000001")
_GREEK_QUANTUM = Decimal("0.000000000001")


def normalize_ibkr_bundle(payload: dict[str, object]) -> MarketSnapshot:
    """Normalize one validated raw connector bundle."""
    if "schema_version" not in payload:
        raise ValueError("bundle is missing required field schema_version")
    _validate_keys(payload, _TOP_LEVEL_KEYS, {"schema_version", "ticker", "underlying", "options"}, "bundle")
    if payload["schema_version"] != 1 or isinstance(payload["schema_version"], bool):
        raise ValueError("schema_version must be 1")
    ticker = _ticker(payload["ticker"])
    notes = list(_notes(payload.get("notes", [])))

    underlying_envelope = _mapping(payload["underlying"], "underlying")
    _validate_keys(
        underlying_envelope,
        _UNDERLYING_KEYS,
        _UNDERLYING_KEYS,
        "underlying",
    )
    underlying_response = _mapping(
        underlying_envelope["response"], "underlying.response"
    )
    last = _mapping(underlying_response.get("last"), "underlying.response.last")
    underlying_price = _money(
        _required_decimal(
            last.get("price"), "underlying price", strictly_positive=True
        ),
        "underlying price",
    )
    underlying_source_timestamp = _epoch_timestamp(
        last.get("ts"), "underlying source timestamp"
    )
    underlying_retrieved_at = _retrieved_at(
        underlying_envelope["retrieved_at"], "underlying.retrieved_at"
    )
    underlying_status = _required_status(
        underlying_response.get("top-status"), "underlying status"
    )
    underlying = UnderlyingQuote(
        ticker=ticker,
        price=underlying_price,
        source="ibkr",
        source_timestamp=underlying_source_timestamp,
        retrieved_at=underlying_retrieved_at,
        status=underlying_status,
    )

    raw_options = payload["options"]
    if not isinstance(raw_options, list):
        raise TypeError("options must be a JSON array")
    identities: set[tuple[date, Decimal, str]] = set()
    options: list[OptionQuote] = []
    retrieved_times = [underlying_retrieved_at]
    skipped = 0
    missing_timestamps = 0
    missing_iv = 0
    missing_oi = 0
    missing_volume = 0
    for index, raw_option in enumerate(raw_options):
        envelope = _mapping(raw_option, f"options[{index}]")
        _validate_keys(envelope, _OPTION_KEYS, _OPTION_KEYS, f"options[{index}]")
        expiration = _expiration(envelope["expiration"], index)
        if expiration < underlying_source_timestamp.date():
            raise ValueError(f"options[{index}].expiration predates the underlying quote")
        strike = _money(
            _required_decimal(
                envelope["strike"],
                f"options[{index}].strike",
                strictly_positive=True,
            ),
            f"options[{index}].strike",
        )
        option_type = _option_type(envelope["option_type"], index)
        identity = (expiration, strike, option_type)
        if identity in identities:
            raise ValueError("bundle contains duplicate option identity")
        identities.add(identity)
        retrieved_at = _retrieved_at(
            envelope["retrieved_at"], f"options[{index}].retrieved_at"
        )
        retrieved_times.append(retrieved_at)
        response = _mapping(envelope["response"], f"options[{index}].response")
        bid_ask_value = response.get("bid-ask")
        if not isinstance(bid_ask_value, Mapping):
            skipped += 1
            continue
        raw_bid = _optional_decimal(bid_ask_value.get("bid"), nonnegative=True)
        raw_ask = _optional_decimal(bid_ask_value.get("ask"), nonnegative=True)
        bid = _money(raw_bid, f"options[{index}] bid") if raw_bid is not None else None
        ask = _money(raw_ask, f"options[{index}] ask") if raw_ask is not None else None
        if bid is None or ask is None or ask < bid:
            skipped += 1
            continue

        source_timestamp = _optional_epoch_timestamp(bid_ask_value.get("ts"))
        implied_volatility = None
        open_interest = _open_interest(response.get("option-open-interest"), option_type)
        volume = _optional_count(response.get("volume"), "volume")
        if source_timestamp is None:
            missing_timestamps += 1
        if implied_volatility is None:
            missing_iv += 1
        if open_interest is None:
            missing_oi += 1
        if volume is None:
            missing_volume += 1
        greeks = _greeks(response.get("option-greeks"))
        options.append(
            OptionQuote(
                ticker=ticker,
                expiration=expiration,
                strike=strike,
                option_type=cast(Literal["CALL", "PUT"], option_type),
                bid=bid,
                ask=ask,
                volume=volume,
                open_interest=open_interest,
                implied_volatility=implied_volatility,
                delta=greeks["delta"],
                gamma=greeks["gamma"],
                theta=greeks["theta"],
                vega=greeks["vega"],
                source="ibkr",
                source_timestamp=source_timestamp,
                retrieved_at=retrieved_at,
                status=_optional_status(response.get("top-status")),
            )
        )

    if not options:
        raise ValueError("IBKR bundle contains no usable option quotes")
    if skipped:
        notes.append(
            f"Skipped {skipped} option quotes with missing, invalid, or crossed bid/ask."
        )
    _append_missing_note(notes, missing_timestamps, "bid/ask source timestamp")
    if missing_iv:
        notes.append(
            "IBKR connector IV units are unspecified; implied volatility was not imported."
        )
    _append_missing_note(notes, missing_oi, "open interest")
    _append_missing_note(notes, missing_volume, "volume")

    try:
        canonical_payload = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as error:
        raise ValueError("IBKR bundle must contain valid JSON values") from error
    return MarketSnapshot(
        snapshot_id=uuid5(_BUNDLE_NAMESPACE, canonical_payload),
        underlying=underlying,
        options=tuple(options),
        created_at=max(retrieved_times),
        notes=tuple(notes),
    )


def _validate_keys(
    value: Mapping[str, object],
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    extra = sorted(keys - allowed)
    if missing:
        raise ValueError(f"{label} is missing required field {missing[0]}")
    if extra:
        raise ValueError(f"{label} contains unsupported field {extra[0]}")


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a JSON object")
    return cast(Mapping[str, object], value)


def _ticker(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("ticker must be a safe symbol")
    ticker = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]*", ticker):
        raise ValueError("ticker must be a safe symbol")
    return ticker


def _notes(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(note, str) and bool(note.strip()) for note in value
    ):
        raise ValueError("notes must be an array of non-blank strings")
    return tuple(cast(str, note) for note in value)


def _required_decimal(
    value: object, label: str, *, strictly_positive: bool = False
) -> Decimal:
    parsed = _optional_decimal(value, nonnegative=not strictly_positive)
    if parsed is None or (strictly_positive and parsed <= 0):
        raise ValueError(f"{label} must be a finite positive number")
    return parsed


def _optional_decimal(value: object, *, nonnegative: bool = False) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    if not parsed.is_finite() or (nonnegative and parsed < 0):
        return None
    return parsed


def _money(value: Decimal, label: str) -> Decimal:
    """Round connector monetary values to the Parquet contract's 10-place scale."""
    try:
        return value.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)
    except InvalidOperation as error:
        raise ValueError(f"{label} exceeds supported storage precision") from error


def _epoch_timestamp(value: object, label: str) -> datetime:
    timestamp = _optional_epoch_timestamp(value)
    if timestamp is None:
        raise ValueError(f"{label} must be a finite epoch timestamp")
    return timestamp


def _optional_epoch_timestamp(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    try:
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _retrieved_at(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO UTC timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO UTC timestamp") from error
    offset = timestamp.utcoffset()
    if timestamp.tzinfo is None or offset is None:
        raise ValueError(f"{label} must be an ISO UTC timestamp")
    if offset.total_seconds() != 0:
        raise ValueError(f"{label} must be an ISO UTC timestamp")
    return timestamp.astimezone(UTC)


def _required_status(value: object, label: str) -> MarketDataStatus:
    section = _mapping(value, label)
    status = section.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError(f"{label} must be a non-blank string")
    return _status(status)


def _optional_status(value: object) -> MarketDataStatus:
    if not isinstance(value, Mapping):
        return MarketDataStatus.UNAVAILABLE
    status = value.get("status")
    if not isinstance(status, str) or not status.strip():
        return MarketDataStatus.UNAVAILABLE
    return _status(status)


def _status(value: str) -> MarketDataStatus:
    try:
        return MarketDataStatus(value.strip().upper())
    except ValueError:
        return MarketDataStatus.UNAVAILABLE


def _expiration(value: object, index: int) -> date:
    if not isinstance(value, str):
        raise TypeError(f"options[{index}].expiration must be YYYY-MM-DD")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError(f"options[{index}].expiration must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"options[{index}].expiration must be YYYY-MM-DD") from error


def _option_type(value: object, index: int) -> str:
    if not isinstance(value, str) or value not in {"CALL", "PUT"}:
        raise ValueError(f"options[{index}].option_type must be CALL or PUT")
    return value


def _optional_count(value: object, field: str) -> int | None:
    if not isinstance(value, Mapping):
        return None
    parsed = _optional_decimal(value.get(field), nonnegative=True)
    if parsed is None or parsed != parsed.to_integral_value():
        return None
    return int(parsed)


def _open_interest(value: object, option_type: str) -> int | None:
    field = "callInterest" if option_type == "CALL" else "putInterest"
    return _optional_count(value, field)


def _greeks(value: object) -> dict[str, Decimal | None]:
    fields = ("delta", "gamma", "theta", "vega")
    if not isinstance(value, Mapping):
        return {field: None for field in fields}
    return {field: _stored_greek(value.get(field)) for field in fields}


def _stored_greek(value: object) -> Decimal | None:
    """Round a finite Greek to decimal128(28, 12), or preserve it as unknown."""
    parsed = _optional_decimal(value)
    if parsed is None:
        return None
    try:
        return parsed.quantize(_GREEK_QUANTUM, rounding=ROUND_HALF_EVEN)
    except InvalidOperation:
        return None


def _append_missing_note(notes: list[str], count: int, field: str) -> None:
    if count:
        noun = "quote" if count == 1 else "quotes"
        notes.append(f"{count} usable option {noun} lacked {field}.")
