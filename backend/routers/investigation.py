"""
WBS BPKH AI - Investigation Router
===================================
Investigation data management endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime
from loguru import logger

from config import GENERIC_ERROR_MESSAGE
from database import report_repo
from auth import require_min_role, UserRole, TokenData

router = APIRouter(prefix="/api/v1/reports", tags=["Investigation"])


@router.get("/{report_id}/investigation")
async def get_investigation_data(
    report_id: str,
    current_user: TokenData = Depends(require_min_role(UserRole.INVESTIGATOR)),
):
    """Get investigation data (evidence, interviews, findings) for a report."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        metadata = report.get("metadata") or {}
        investigation = metadata.get("investigation", {
            "evidence": [], "interviews": [], "findings": [],
            "timeline": [], "recommendations": {}, "management_response": "",
        })
        return investigation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get investigation data: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.put("/{report_id}/investigation")
async def save_investigation_data(
    report_id: str,
    request: Request,
    current_user: TokenData = Depends(require_min_role(UserRole.INVESTIGATOR)),
):
    """Save investigation data for a report."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        body = await request.json()

        allowed_keys = {
            "evidence", "interviews", "findings",
            "timeline", "recommendations", "management_response",
        }
        investigation = {k: v for k, v in body.items() if k in allowed_keys}

        metadata = report.get("metadata") or {}
        metadata["investigation"] = investigation

        report_repo.db.table("reports").update({
            "metadata": metadata,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", report_id).execute()

        await report_repo._create_audit_log(
            report_id, "INVESTIGATION_DATA_UPDATED",
            {"updated_by": current_user.email, "keys": list(investigation.keys())},
        )
        return {"message": "Data investigasi berhasil disimpan"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save investigation data: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
