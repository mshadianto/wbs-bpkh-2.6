"""
WBS BPKH AI - Tickets Router
=============================
Public endpoints for whistleblowers to track and communicate on reports.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from config import GENERIC_ERROR_MESSAGE, STATUS_DESCRIPTIONS
from database import report_repo, message_repo
from models import MessageCreate, TicketLookup, TicketStatusResponse

router = APIRouter(prefix="/api/v1/tickets", tags=["Tickets"])


@router.post("/lookup", response_model=TicketStatusResponse)
async def lookup_ticket(lookup: TicketLookup):
    """Public endpoint for whistleblowers to check their report status."""
    try:
        report = await report_repo.get_by_ticket_id(lookup.ticket_id)
        if not report:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Parse involved_parties safely (DB column = involved_parties)
        parties_raw = report.get("involved_parties") or report.get("parties_involved") or []
        if isinstance(parties_raw, str):
            import json
            try:
                parties_raw = json.loads(parties_raw)
            except (json.JSONDecodeError, TypeError):
                parties_raw = [parties_raw] if parties_raw.strip() else []

        # Map DB column names to response fields
        # DB: title → subject, involved_parties → parties_involved
        return TicketStatusResponse(
            ticket_id=report["ticket_id"],
            status=report["status"],
            status_description=STATUS_DESCRIPTIONS.get(
                report["status"], "Status sedang diproses",
            ),
            category=report.get("category"),
            subject=report.get("title") or report.get("subject"),
            description=report.get("description"),
            severity=report.get("severity"),
            channel=report.get("channel"),
            incident_date=report.get("incident_date"),
            incident_location=report.get("incident_location"),
            parties_involved=parties_raw if isinstance(parties_raw, list) else [],
            created_at=report.get("created_at"),
            last_updated=report["updated_at"],
            can_add_info=report["status"] in ["NEW", "REVIEWING", "NEED_INFO"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ticket lookup failed: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.post("/{ticket_id}/messages")
async def add_message_by_ticket(ticket_id: str, message: MessageCreate):
    """Add message/additional info using ticket ID (Public)."""
    try:
        report = await report_repo.get_by_ticket_id(ticket_id)
        if not report:
            raise HTTPException(status_code=404, detail="Ticket not found")

        if report["status"] not in ["NEW", "REVIEWING", "NEED_INFO"]:
            raise HTTPException(
                status_code=400,
                detail="Tidak dapat menambah informasi pada status ini",
            )

        msg = await message_repo.create(
            report_id=report["id"], content=message.content,
            sender_type="REPORTER", attachments=message.attachments,
            ticket_id=ticket_id,
        )
        return {"message": "Informasi berhasil ditambahkan", "message_id": msg["id"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.get("/{ticket_id}/messages")
async def get_messages_by_ticket(ticket_id: str):
    """Get messages for a ticket (Public - filtered for reporter)."""
    try:
        report = await report_repo.get_by_ticket_id(ticket_id)
        if not report:
            raise HTTPException(status_code=404, detail="Ticket not found")

        messages = await message_repo.get_by_report(report["id"])

        public_messages = [
            {
                "id": m["id"],
                "content": m["content"],
                "sender": "Anda" if m["sender_type"] == "REPORTER" else "Tim WBS",
                "created_at": m["created_at"],
            }
            for m in messages
            if m["sender_type"] in ["REPORTER", "ADMIN"]
        ]
        return {"messages": public_messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
