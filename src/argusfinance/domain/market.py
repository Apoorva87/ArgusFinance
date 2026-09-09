"""Immutable, provider-neutral market data value objects."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MarketDataStatus(str, Enum):
    """Freshness state reported by a market-data source."""

    REALTIME = "REALTIME"
    DELAYED = "DELAYED"
    FROZEN = "FROZEN"
    FROZEN_DELAYED = "FROZEN_DELAYED"
    UNAVAILABLE = "UNAVAILABLE"


class _MarketValue(BaseModel):
    """Common invariants for immutable, normalized market values."""

    model_config = ConfigDict(frozen=True)

    @field_validator("source_timestamp", "retrieved_at", "created_at", check_fields=False)
    @classmethod
    def _timestamps_must_be_timezone_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)


class UnderlyingQuote(_MarketValue):
    """A normalized underlying equity quote and its provenance."""

    ticker: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    source: str = Field(min_length=1)
    source_timestamp: datetime
    retrieved_at: datetime
    status: MarketDataStatus

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker must not be blank")
        return normalized


class OptionQuote(_MarketValue):
    """A normalized option-contract quote and its provenance."""

    ticker: str = Field(min_length=1)
    expiration: date
    strike: Decimal = Field(gt=0)
    option_type: Literal["CALL", "PUT"]
    bid: Decimal = Field(ge=0)
    ask: Decimal = Field(ge=0)
    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, ge=0)
    implied_volatility: Decimal | None = Field(default=None, ge=0)
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    source: str = Field(min_length=1)
    source_timestamp: datetime | None = None
    retrieved_at: datetime
    status: MarketDataStatus

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker must not be blank")
        return normalized

    @model_validator(mode="after")
    def _ask_must_not_be_below_bid(self) -> "OptionQuote":
        if self.ask < self.bid:
            raise ValueError("ask must be greater than or equal to bid")
        return self


class MarketSnapshot(_MarketValue):
    """A complete immutable snapshot of an underlying and option chain."""

    snapshot_id: UUID
    underlying: UnderlyingQuote
    options: tuple[OptionQuote, ...]
    created_at: datetime
    notes: tuple[str, ...] = ()

    @field_validator("options")
    @classmethod
    def _validate_and_order_options(
        cls, options: tuple[OptionQuote, ...]
    ) -> tuple[OptionQuote, ...]:
        if not options:
            raise ValueError("snapshot must contain at least one option quote")

        identities: set[tuple[str, date, Decimal, str]] = set()
        for option in options:
            identity = (
                option.ticker,
                option.expiration,
                option.strike,
                option.option_type,
            )
            if identity in identities:
                raise ValueError("snapshot contains duplicate option identity")
            identities.add(identity)

        return tuple(
            sorted(
                options,
                key=lambda option: (
                    option.expiration,
                    option.strike,
                    option.option_type,
                ),
            )
        )

    @model_validator(mode="after")
    def _option_tickers_must_match_underlying(self) -> "MarketSnapshot":
        if any(option.ticker != self.underlying.ticker for option in self.options):
            raise ValueError("option ticker must match underlying ticker")
        return self
