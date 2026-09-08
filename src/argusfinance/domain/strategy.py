"""Typed, immutable contracts for deterministic option-strategy research."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from argusfinance.domain.market import MarketDataStatus


class StrategyStatus(str, Enum):
    WATCH = "WATCH"
    PAPER = "PAPER"
    REAL_MANUAL = "REAL_MANUAL"
    SHADOW = "SHADOW"


class Pricing(str, Enum):
    NATURAL = "NATURAL"
    MIDPOINT = "MIDPOINT"


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class LegSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class BoundaryKind(str, Enum):
    PRICE_BELOW = "PRICE_BELOW"
    PRICE_ABOVE = "PRICE_ABOVE"
    REVIEW_DATE = "REVIEW_DATE"


class _StrategyValue(BaseModel):
    model_config = ConfigDict(frozen=True)


FiniteDecimal = Annotated[Decimal, Field(allow_inf_nan=False)]


class OptionLeg(_StrategyValue):
    expiration: date
    strike: FiniteDecimal = Field(gt=0)
    option_type: OptionType
    side: LegSide
    quantity: int = Field(ge=1, le=100)


class StrategyBoundary(_StrategyValue):
    kind: BoundaryKind
    value: str = Field(min_length=1)
    note: str = Field(min_length=1, max_length=500)

    @field_validator("note")
    @classmethod
    def note_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("boundary note must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_value(self) -> "StrategyBoundary":
        if self.kind is BoundaryKind.REVIEW_DATE:
            try:
                date.fromisoformat(self.value)
            except ValueError as error:
                raise ValueError("review date must be ISO YYYY-MM-DD") from error
        else:
            try:
                value = Decimal(self.value)
            except Exception as error:
                raise ValueError("price boundary must be a decimal string") from error
            if not value.is_finite() or value <= 0:
                raise ValueError("price boundary must be positive and finite")
        return self


class StrategyDraft(_StrategyValue):
    snapshot_id: UUID
    name: str = Field(min_length=1, max_length=120)
    status: StrategyStatus
    thesis: str = Field(default="", max_length=4000)
    pricing: Pricing = Pricing.NATURAL
    fee_per_contract: FiniteDecimal = Field(default=Decimal(0), ge=0)
    legs: tuple[OptionLeg, ...] = Field(min_length=1, max_length=4)
    boundaries: tuple[StrategyBoundary, ...] = Field(default=(), max_length=10)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def legs_must_not_duplicate_or_net(self) -> "StrategyDraft":
        identities: set[tuple[date, Decimal, OptionType]] = set()
        for leg in self.legs:
            identity = (leg.expiration, leg.strike, leg.option_type)
            if identity in identities:
                raise ValueError("duplicate contract or offsetting contract rows are not allowed")
            identities.add(identity)
        return self


class ResolvedLeg(_StrategyValue):
    expiration: date
    strike: Decimal
    option_type: OptionType
    side: LegSide
    quantity: int
    entry_premium: Decimal
    delta: Decimal | None
    gamma: Decimal | None
    theta: Decimal | None
    vega: Decimal | None


class NetGreeks(_StrategyValue):
    delta: Decimal | None
    gamma: Decimal | None
    theta: Decimal | None
    vega: Decimal | None


class PayoffPoint(_StrategyValue):
    spot: Decimal
    pnl: Decimal


class StrategyEvaluation(_StrategyValue):
    snapshot_id: UUID
    ticker: str
    expiration: date
    spot: Decimal
    pricing: Pricing
    legs: tuple[ResolvedLeg, ...]
    net_debit: Decimal
    entry_fees: Decimal
    maximum_profit: Decimal | None
    maximum_loss: Decimal | None
    breakevens: list[Decimal]
    payoff_points: list[PayoffPoint]
    net_greeks: NetGreeks
    warnings: list[str]
    eligible: bool
    analytics_version: str
    source_timestamp: datetime
    source_status: MarketDataStatus
    boundaries: tuple[StrategyBoundary, ...]

    @field_validator("source_timestamp")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("source timestamp must be timezone-aware")
        return value.astimezone(UTC)


class SavedStrategy(_StrategyValue):
    id: UUID
    created_at: datetime
    draft: StrategyDraft
    evaluation: StrategyEvaluation

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)
