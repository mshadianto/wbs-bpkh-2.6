"""
WBS BPKH AI - Reports Router
=============================
CRUD operations for whistleblowing reports.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from io import StringIO
from loguru import logger
import csv

from config import (
    get_allowed_status_transitions, GENERIC_ERROR_MESSAGE, STATUS_DESCRIPTIONS,
)
from database import report_repo, message_repo
from models import (
    ReportCreate, ReportResponse, ReportDetail, ReportListResponse,
    MessageCreate, StatusUpdate,
)
from auth import (
    require_min_role, require_role, UserRole, TokenData, can_update_status,
)

router = APIRouter(prefix="/api/v1", tags=["Reports"])


def _sanitize_csv_value(val) -> str:
    """Prevent CSV injection by escaping formula-triggering characters."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


@router.post("/reports", response_model=ReportResponse)
async def create_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks,
):
    """Submit new whistleblowing report. AI analysis runs in background."""
    try:
        report_data = report.model_dump()
        created_report = await report_repo.create(report_data)

        # Import here to avoid circular imports
        from services.background_tasks import run_ai_analysis
        from rag import RAGRetriever

        background_tasks.add_task(
            run_ai_analysis,
            created_report["id"],
            report.description,
            RAGRetriever(),
        )

        logger.info(f"Report created: {created_report['ticket_id']}")

        return ReportResponse(
            id=created_report["id"],
            ticket_id=created_report["ticket_id"],
            channel=created_report["channel"],
            status=created_report["status"],
            subject=created_report.get("title", ""),
            description=created_report["description"][:200] + "...",
            is_anonymous=created_report["is_anonymous"],
            created_at=created_report["created_at"],
            updated_at=created_report["updated_at"],
        )
    except Exception as e:
        logger.error(f"Failed to create report: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """List all reports with search and filters (Intake Officer+)."""
    try:
        offset = (page - 1) * per_page
        filter_kwargs = dict(
            status=status, severity=severity, category=category,
            search=search, date_from=date_from, date_to=date_to,
            assigned_to=assigned_to,
        )

        total_count = await report_repo.get_total_count(**filter_kwargs)
        reports = await report_repo.list_all(
            **filter_kwargs,
            sort_by=sort_by or "created_at",
            sort_order=sort_order or "desc",
            limit=per_page, offset=offset,
        )

        return ReportListResponse(
            total=total_count,
            reports=[ReportResponse(**r) for r in reports],
            page=page, per_page=per_page,
        )
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.get("/reports/export")
async def export_reports(
    format: str = Query("csv"),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_min_role(UserRole.MANAGER)),
):
    """Export reports as CSV (Manager+)."""
    try:
        reports = await report_repo.list_all(
            status=status, severity=severity, category=category, limit=5000,
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Ticket ID", "Status", "Severity", "Category", "Subject",
            "Channel", "Is Anonymous", "Fraud Score", "Assigned To",
            "Created At", "Updated At",
        ])
        for r in reports:
            writer.writerow([
                _sanitize_csv_value(r.get("ticket_id", "")),
                _sanitize_csv_value(r.get("status", "")),
                _sanitize_csv_value(r.get("severity", "")),
                _sanitize_csv_value(r.get("category", "")),
                _sanitize_csv_value(r.get("title", "")),
                _sanitize_csv_value(r.get("channel", "")),
                r.get("is_anonymous", ""),
                r.get("fraud_score", ""),
                _sanitize_csv_value(r.get("assigned_to", "")),
                r.get("created_at", ""),
                r.get("updated_at", ""),
            ])

        output.seek(0)
        filename = f"wbs_reports_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"Failed to export reports: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: str,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """Get report details (Intake Officer+)."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        messages = await message_repo.get_by_report(report_id)
        return ReportDetail(**report, messages_count=len(messages))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.patch("/reports/{report_id}/status")
async def update_report_status(
    report_id: str,
    update: StatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """Update report status (Intake Officer+)."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        current_status = report.get("status", "NEW")
        new_status = update.new_status.value

        allowed_transitions = get_allowed_status_transitions(current_status)
        if new_status not in allowed_transitions:
            raise HTTPException(
                status_code=400,
                detail=f"Transisi status tidak valid: {current_status} → {new_status}. "
                       f"Status yang diperbolehkan: {', '.join(allowed_transitions) if allowed_transitions else 'tidak ada (status final)'}",
            )

        if not can_update_status(current_user, current_status, new_status):
            raise HTTPException(
                status_code=403,
                detail=f"Role {current_user.role.value} tidak memiliki izin untuk transisi {current_status} → {new_status}",
            )

        await report_repo.update_status(report_id, new_status, updated_by=current_user.email)

        # Send notification in background
        from services import NotificationService
        notification_service = NotificationService()
        ticket_id = report.get("ticket_id")
        reporter_phone = report.get("reporter_phone")
        reporter_email = report.get("reporter_email")
        if ticket_id and (reporter_phone or reporter_email):
            background_tasks.add_task(
                notification_service.send_status_update,
                ticket_id=ticket_id, old_status=current_status,
                new_status=new_status, reporter_phone=reporter_phone,
                reporter_email=reporter_email, note=update.notes,
            )

        return {"message": "Status updated", "new_status": new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.post("/reports/{report_id}/messages")
async def add_admin_message(
    report_id: str,
    message: MessageCreate,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """Send a message to a reporter (Intake Officer+)."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        msg = await message_repo.create(
            report_id=report_id, content=message.content,
            sender_type="ADMIN", ticket_id=report.get("ticket_id"),
        )
        return {"message": "Pesan terkirim", "data": msg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send admin message: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.post("/reports/{report_id}/assign")
async def assign_report(
    report_id: str,
    assigned_to: str = Query(..., description="User ID to assign to"),
    current_user: TokenData = Depends(require_min_role(UserRole.MANAGER)),
):
    """Assign a report to an investigator (Manager+)."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        report_repo.db.table("reports").update({
            "assigned_to": assigned_to,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", report_id).execute()

        try:
            report_repo.db.table("report_assignments").insert({
                "report_id": report_id,
                "assigned_to": assigned_to,
                "assigned_by": current_user.user_id,
                "role": "INVESTIGATOR",
            }).execute()
        except Exception as assign_err:
            logger.warning(f"Failed to create assignment record: {assign_err}")

        await report_repo._create_audit_log(
            report_id, "REPORT_ASSIGNED",
            {"assigned_to": assigned_to, "assigned_by": current_user.email},
        )
        return {"message": "Laporan berhasil di-assign", "assigned_to": assigned_to}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign report: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
