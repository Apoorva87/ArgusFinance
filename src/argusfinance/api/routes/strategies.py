"""HTTP contract for snapshot-backed strategy evaluation and saved research."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from argusfinance.api.dependencies import get_strategy_service
from argusfinance.domain.strategy import (
    SavedStrategy,
    StrategyDraft,
    StrategyEvaluation,
)
from argusfinance.services.strategies import (
    StrategyInputError,
    StrategyNotFoundError,
    StrategyService,
    StrategySnapshotNotFoundError,
)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.post("/evaluate", response_model=StrategyEvaluation)
def evaluate_strategy(
    draft: StrategyDraft,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyEvaluation:
    """Evaluate selected immutable snapshot quotes without persisting a strategy."""
    try:
        return service.evaluate(draft)
    except StrategySnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except StrategyInputError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.post("", response_model=SavedStrategy, status_code=status.HTTP_201_CREATED)
def save_strategy(
    draft: StrategyDraft,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> SavedStrategy:
    """Save the draft and its exact entry evaluation atomically."""
    try:
        return service.save(draft)
    except StrategySnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except StrategyInputError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("", response_model=list[SavedStrategy])
def list_strategies(
    service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> list[SavedStrategy]:
    """List saved research documents newest first."""
    return service.list()


@router.get("/{strategy_id}", response_model=SavedStrategy)
def get_strategy(
    strategy_id: UUID,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> SavedStrategy:
    """Get one saved record without recalculating it from current evidence."""
    try:
        return service.get(strategy_id)
    except StrategyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
