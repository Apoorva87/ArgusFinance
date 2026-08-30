"""HTTP contract for shared market snapshot workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from argusfinance.api.dependencies import get_market_service
from argusfinance.domain.market import MarketSnapshot
from argusfinance.services.market import (
    LatestSnapshotNotFoundError,
    MarketService,
    ProviderInputError,
)

router = APIRouter(prefix="/api/market", tags=["market"])


@router.post("/{ticker}/snapshots", response_model=MarketSnapshot, status_code=status.HTTP_201_CREATED)
def capture_snapshot(
    ticker: str,
    service: Annotated[MarketService, Depends(get_market_service)],
    weeks: int = 8,
) -> MarketSnapshot:
    """Capture and persist a deterministic provider snapshot."""
    try:
        return service.capture(ticker, weeks)
    except ProviderInputError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("/{ticker}/latest", response_model=MarketSnapshot)
def get_latest_snapshot(
    ticker: str,
    service: Annotated[MarketService, Depends(get_market_service)],
) -> MarketSnapshot:
    """Return the exact persisted snapshot referenced by latest metadata."""
    try:
        return service.latest(ticker)
    except LatestSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
