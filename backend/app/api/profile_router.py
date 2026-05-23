"""
Investor Profile API router.
Endpoints: create, get, update profile, and compute risk score.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    RiskScoreResponse,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Investor Profile"])


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_profile(
    data: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new investor profile for the authenticated user."""
    return await ProfileService.create_profile(db, current_user.id, data)


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the investor profile for the authenticated user."""
    return await ProfileService.get_profile(db, current_user.id)


@router.put("", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially update the investor profile."""
    return await ProfileService.update_profile(db, current_user.id, data)


@router.get("/risk-score", response_model=RiskScoreResponse)
async def get_risk_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute and return a quantitative risk score (0-100) based on
    weighted factors: age, income-to-debt ratio, investment horizon,
    and explicit risk appetite.
    """
    return await ProfileService.compute_risk_score(db, current_user.id)
