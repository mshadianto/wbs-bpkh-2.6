"""
WBS BPKH AI - Dashboard Router
===============================
Dashboard statistics and audit log endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from loguru import logger

from config import GENERIC_ERROR_MESSAGE
from database import report_repo
from models import DashboardStats
from auth import require_min_role, UserRole, TokenData

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """Get dashboard statistics (Intake Officer+)."""
    try:
        stats = await report_repo.get_statistics()
        sla_at_risk = await report_repo.get_sla_at_risk_count()

        return DashboardStats(
            total_reports=stats["total"],
            by_status=stats["by_status"],
            by_severity=stats["by_severity"],
            by_category=stats["by_category"],
            pending_review=stats["by_status"].get("NEW", 0)
                         + stats["by_status"].get("REVIEWING", 0),
            sla_at_risk=sla_at_risk,
            active_investigations=stats.get("active_investigations", 0),
            closure_rate=stats.get("closure_rate", 0.0),
            recent_reports_7d=stats.get("recent_reports_7d", 0),
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.get("/audit-logs")
async def get_audit_logs(
    report_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_min_role(UserRole.MANAGER)),
):
    """Query audit logs with filters (Manager+)."""
    try:
        offset = (page - 1) * per_page
        result = await report_repo.get_audit_logs(
            report_id=report_id, action=action,
            date_from=date_from, date_to=date_to,
            limit=per_page, offset=offset,
        )
        return {
            "logs": result["logs"],
            "total": result["total"],
            "page": page,
            "per_page": per_page,
        }
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
