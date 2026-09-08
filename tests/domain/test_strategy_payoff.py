"""Golden expiration-payoff contracts for saved strategy research."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from argusfinance.analytics.payoff import evaluate_expiration_payoff
from argusfinance.domain.strategy import (
    LegSide,
    OptionLeg,
    OptionType,
    Pricing,
    StrategyDraft,
    StrategyStatus,
)


def test_bull_call_vertical_has_hand_checked_natural_payoff() -> None:
    """A missing entry-cashflow or capped-upside branch must fail this golden case."""
    draft = StrategyDraft(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="NVDA vertical",
        status=StrategyStatus.PAPER,
        pricing=Pricing.NATURAL,
        legs=(
            OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(175), option_type=OptionType.CALL, side=LegSide.BUY, quantity=1),
            OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(185), option_type=OptionType.CALL, side=LegSide.SELL, quantity=1),
        ),
    )

    result = evaluate_expiration_payoff(
        draft,
        [
            (draft.legs[0], Decimal("8.80"), Decimal("0.64"), Decimal("0.012"), Decimal("-0.15"), Decimal("0.21")),
            (draft.legs[1], Decimal("3.75"), Decimal("0.42"), Decimal("0.013"), Decimal("-0.14"), Decimal("0.22")),
        ],
        Decimal("180.25"),
    )

    assert result.net_debit == Decimal(505)
    assert result.maximum_loss == Decimal(505)
    assert result.maximum_profit == Decimal(495)
    assert result.breakevens == [Decimal("180.05")]


def test_long_call_has_unlimited_profit_and_quantity_scaled_fees() -> None:
    """Treating an upward call tail as finite or omitting contract fees must fail."""
    leg = OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(175), option_type=OptionType.CALL, side=LegSide.BUY, quantity=2)
    draft = StrategyDraft(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Long calls",
        status=StrategyStatus.PAPER,
        fee_per_contract=Decimal("1.25"),
        legs=(leg,),
    )

    result = evaluate_expiration_payoff(draft, [(leg, Decimal("8.80"), None, None, None, None)], Decimal("180.25"))

    assert result.net_debit == Decimal("1762.50")
    assert result.entry_fees == Decimal("2.50")
    assert result.maximum_profit is None
    assert result.maximum_loss == Decimal("1762.50")
    assert result.breakevens == [Decimal("183.8125")]
    assert result.net_greeks.delta is None


def test_zero_payoff_plateau_is_not_returned_as_a_made_up_root() -> None:
    """A whole zero interval must be labelled, not collapsed into fake isolated roots."""
    buy = OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(175), option_type=OptionType.CALL, side=LegSide.BUY, quantity=1)
    sell = OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(185), option_type=OptionType.CALL, side=LegSide.SELL, quantity=1)
    draft = StrategyDraft(snapshot_id=UUID("00000000-0000-0000-0000-000000000001"), name="Free spread", status=StrategyStatus.PAPER, legs=(buy, sell))

    result = evaluate_expiration_payoff(
        draft,
        [(buy, Decimal(0), None, None, None, None), (sell, Decimal(0), None, None, None, None)],
        Decimal(180),
    )

    assert result.breakevens == []
    assert result.warnings == ["Zero P&L interval from 0 to 175; no isolated breakeven"]


def test_long_put_has_finite_zero_spot_profit_and_infinite_zero_pnl_interval() -> None:
    """Treating the high put plateau as an isolated root or unbounded profit is incorrect."""
    leg = OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(175), option_type=OptionType.PUT, side=LegSide.BUY, quantity=1)
    draft = StrategyDraft(snapshot_id=UUID("00000000-0000-0000-0000-000000000001"), name="Free put", status=StrategyStatus.PAPER, legs=(leg,))

    result = evaluate_expiration_payoff(draft, [(leg, Decimal(0), None, None, None, None)], Decimal(180))

    assert result.maximum_profit == Decimal(17500)
    assert result.maximum_loss == Decimal(0)
    assert result.breakevens == []
    assert result.warnings == ["Zero P&L interval from 175 to infinity; no isolated breakeven"]


def test_long_call_plot_includes_illustrative_profitable_tail_point() -> None:
    """A plot ending at the break-even conceals the upward expiration tail."""
    leg = OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(175), option_type=OptionType.CALL, side=LegSide.BUY, quantity=1)
    draft = StrategyDraft(snapshot_id=UUID("00000000-0000-0000-0000-000000000001"), name="Long call plot", status=StrategyStatus.PAPER, legs=(leg,))

    result = evaluate_expiration_payoff(draft, [(leg, Decimal("8.80"), None, None, None, None)], Decimal("180.25"))

    assert result.payoff_points[-1].spot > Decimal("183.80")
    assert result.payoff_points[-1].pnl > Decimal(0)


@pytest.mark.parametrize("option_type,profit,loss,root", [
    (OptionType.CALL, Decimal(880), None, Decimal("183.80")),
    (OptionType.PUT, Decimal(880), Decimal(16620), Decimal("166.20")),
])
def test_short_option_credit_and_tail_risk(option_type, profit, loss, root) -> None:
    leg = OptionLeg(expiration=date(2026, 9, 18), strike=Decimal(175), option_type=option_type, side=LegSide.SELL, quantity=1)
    draft = StrategyDraft(snapshot_id=UUID("00000000-0000-0000-0000-000000000001"), name="Short option", status=StrategyStatus.WATCH, legs=(leg,))
    result = evaluate_expiration_payoff(draft, [(leg, Decimal("8.80"), None, None, None, None)], Decimal("180.25"))
    assert result.net_debit == Decimal(-880)
    assert result.maximum_profit == profit
    assert result.maximum_loss == loss
    assert result.breakevens == [root]
