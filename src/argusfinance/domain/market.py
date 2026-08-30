"""Immutable, provider-neutral market data value objects."""

from datetime import date, datetime
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
    UNAVAILABLE = "UNAVAILABLE"


class _MarketValue(BaseModel):
    """Common invariants for immutable, normalized market values."""

    model_config = ConfigDict(frozen=True)

    @field_validator("source_timestamp", "retrieved_at", "created_at", check_fields=False)
    @classmethod
    def _timestamps_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


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
    volume: int = Field(ge=0)
    open_interest: int = Field(ge=0)
    implied_volatility: Decimal = Field(ge=0)
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
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
