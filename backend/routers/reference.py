"""
WBS BPKH AI - Reference Router
===============================
Static reference data endpoints (statuses, severities, categories).
"""

from fastapi import APIRouter

from config import REPORT_STATUS, SEVERITY_LEVELS, VIOLATION_CATEGORIES

router = APIRouter(prefix="/api/v1/reference", tags=["Reference"])


@router.get("/statuses")
async def get_statuses():
    """Get all possible report statuses."""
    return REPORT_STATUS


@router.get("/severities")
async def get_severities():
    """Get severity levels with SLA."""
    return SEVERITY_LEVELS


@router.get("/categories")
async def get_categories():
    """Get violation categories."""
    return VIOLATION_CATEGORIES
