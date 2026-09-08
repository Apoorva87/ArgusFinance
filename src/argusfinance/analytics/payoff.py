"""Exact expiration payoff arithmetic for finite option-leg selections."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from argusfinance.domain.strategy import (
    LegSide,
    NetGreeks,
    OptionLeg,
    OptionType,
    PayoffPoint,
    ResolvedLeg,
    StrategyDraft,
)

CONTRACT_MULTIPLIER = Decimal(100)


@dataclass(frozen=True)
class PayoffAnalysis:
    legs: tuple[ResolvedLeg, ...]
    net_debit: Decimal
    entry_fees: Decimal
    maximum_profit: Decimal | None
    maximum_loss: Decimal | None
    breakevens: list[Decimal]
    payoff_points: list[PayoffPoint]
    net_greeks: NetGreeks
    warnings: list[str]


def evaluate_expiration_payoff(
    draft: StrategyDraft,
    resolved: Sequence[tuple[OptionLeg, Decimal, Decimal | None, Decimal | None, Decimal | None, Decimal | None]],
    spot: Decimal,
) -> PayoffAnalysis:
    """Calculate expiry-only P/L from selected snapshot premiums and Greeks."""
    if len(resolved) != len(draft.legs):
        raise ValueError("each selected leg requires one resolved snapshot quote")
    fees = _clean(sum((draft.fee_per_contract * leg.quantity for leg, *_ in resolved), Decimal(0)))
    entries = tuple(
        ResolvedLeg(
            expiration=leg.expiration,
            strike=leg.strike,
            option_type=leg.option_type,
            side=leg.side,
            quantity=leg.quantity,
            entry_premium=premium,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
        )
        for leg, premium, delta, gamma, theta, vega in resolved
    )
    debit = _clean(sum(
        (
            (Decimal(1) if leg.side is LegSide.BUY else Decimal(-1))
            * premium
            * leg.quantity
            * CONTRACT_MULTIPLIER
            for leg, premium, *_ in resolved
        ),
        Decimal(0),
    ) + fees)
    strikes = sorted({leg.strike for leg, *_ in resolved})
    roots, plateau_warnings = _roots(resolved, debit, strikes)
    plotted = {Decimal(0), spot, *strikes, *roots}
    high_anchor = max(plotted)
    plotted.add(_clean(high_anchor + max(Decimal(10), high_anchor / Decimal(10))))
    points_spot = sorted(plotted)
    points = [PayoffPoint(spot=value, pnl=_pnl(resolved, debit, value)) for value in points_spot]
    extrema_points = [Decimal(0), *strikes]
    values = [_pnl(resolved, debit, value) for value in extrema_points]
    high_slope = _slope(resolved, Decimal("Infinity"))
    maximum_profit = None if high_slope > 0 else _clean(max(Decimal(0), max(values)))
    maximum_loss = None if high_slope < 0 else _clean(max(Decimal(0), -min(values)))
    # At spot >= 0, only a downward unlimited high tail is possible for loss;
    # finite low end is represented by spot=0 above.
    greeks = _net_greeks(entries)
    return PayoffAnalysis(
        legs=entries,
        net_debit=debit,
        entry_fees=fees,
        maximum_profit=maximum_profit,
        maximum_loss=maximum_loss,
        breakevens=roots,
        payoff_points=points,
        net_greeks=greeks,
        warnings=plateau_warnings,
    )


def _pnl(
    resolved: Sequence[tuple[OptionLeg, Decimal, Decimal | None, Decimal | None, Decimal | None, Decimal | None]],
    debit: Decimal,
    spot: Decimal,
) -> Decimal:
    intrinsic = sum(
        (
            (Decimal(1) if leg.side is LegSide.BUY else Decimal(-1))
            * leg.quantity
            * CONTRACT_MULTIPLIER
            * _intrinsic(leg, spot)
            for leg, *_ in resolved
        ),
        Decimal(0),
    )
    return _clean(intrinsic - debit)


def _intrinsic(leg: OptionLeg, spot: Decimal) -> Decimal:
    if leg.option_type is OptionType.CALL:
        return max(spot - leg.strike, Decimal(0))
    return max(leg.strike - spot, Decimal(0))


def _roots(
    resolved: Sequence[tuple[OptionLeg, Decimal, Decimal | None, Decimal | None, Decimal | None, Decimal | None]],
    debit: Decimal,
    strikes: list[Decimal],
) -> tuple[list[Decimal], list[str]]:
    boundaries = [Decimal(0), *strikes]
    roots: set[Decimal] = set()
    plateau_bounds: set[Decimal] = set()
    warnings: list[str] = []
    for left, right in zip(boundaries, [*strikes, None], strict=True):
        left_value = _pnl(resolved, debit, left)
        if right is None:
            slope = _slope(resolved, left + Decimal(1))
            if left_value == 0 and slope == 0:
                roots.discard(left)
                warnings.append(f"Zero P&L interval from {left} to infinity; no isolated breakeven")
                continue
            if left_value == 0:
                roots.add(left)
            if slope:
                root = _clean(left - left_value / slope)
                if root > left:
                    roots.add(root)
            continue
        right_value = _pnl(resolved, debit, right)
        if left_value == 0 and right_value == 0 and _slope(resolved, left + (right - left) / 2) == 0:
            plateau_bounds.update({left, right})
            warnings.append(f"Zero P&L interval from {left} to {right}; no isolated breakeven")
            continue
        if left_value == 0:
            roots.add(left)
        if right_value == 0:
            roots.add(right)
        if left_value * right_value < 0:
            roots.add(_clean(left + (right - left) * (-left_value) / (right_value - left_value)))
    return sorted(roots - plateau_bounds), warnings


def _slope(
    resolved: Sequence[tuple[OptionLeg, Decimal, Decimal | None, Decimal | None, Decimal | None, Decimal | None]],
    value: Decimal,
) -> Decimal:
    result = Decimal(0)
    for leg, *_ in resolved:
        sign = Decimal(1) if leg.side is LegSide.BUY else Decimal(-1)
        if leg.option_type is OptionType.CALL and value > leg.strike:
            result += sign * leg.quantity * CONTRACT_MULTIPLIER
        if leg.option_type is OptionType.PUT and value < leg.strike:
            result -= sign * leg.quantity * CONTRACT_MULTIPLIER
    return result


def _net_greeks(legs: tuple[ResolvedLeg, ...]) -> NetGreeks:
    def aggregate(name: str) -> Decimal | None:
        values = [getattr(leg, name) for leg in legs]
        if any(value is None for value in values):
            return None
        return _clean(sum(
            (
                (Decimal(1) if leg.side is LegSide.BUY else Decimal(-1))
                * leg.quantity
                * CONTRACT_MULTIPLIER
                * value
                for leg, value in zip(legs, values, strict=True)
                if value is not None
            ),
            Decimal(0),
        ))

    return NetGreeks(delta=aggregate("delta"), gamma=aggregate("gamma"), theta=aggregate("theta"), vega=aggregate("vega"))


def _clean(value: Decimal) -> Decimal:
    """Keep exact decimal arithmetic while emitting stable, non-padded JSON decimals."""
    return value.normalize() if value else Decimal(0)
