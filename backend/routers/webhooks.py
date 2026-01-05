"""
WBS BPKH AI - Webhooks Router
==============================
Endpoints for receiving external webhooks (WhatsApp, Email, etc.)
"""

from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime
import re
import uuid

from database import report_repo, message_repo
from services.notification_service import notification_service
from config import settings

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


# ============== Pydantic Models ==============

class WAHAMessage(BaseModel):
    """WAHA incoming message payload."""
    id: str
    from_: str = Field(alias="from")
    to: str
    body: str
    timestamp: int
    type: str = "chat"

    class Config:
        populate_by_name = True


class WAHAWebhook(BaseModel):
    """WAHA webhook payload."""
    event: str
    session: str
    payload: Dict[str, Any]


class EmailWebhook(BaseModel):
    """Incoming email webhook payload (from email-to-webhook service)."""
    from_email: str = Field(alias="from")
    to: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    attachments: Optional[list] = None
    received_at: Optional[str] = None

    class Config:
        populate_by_name = True


# ============== Helper Functions ==============

def extract_ticket_from_message(text: str) -> Optional[str]:
    """Extract ticket ID from message text."""
    # Pattern: 8 uppercase hex characters
    pattern = r'\b([A-F0-9]{8})\b'
    match = re.search(pattern, text.upper())
    return match.group(1) if match else None


def parse_report_from_text(text: str) -> Dict[str, str]:
    """
    Parse report details from unstructured text.
    Tries to extract subject and description.
    """
    lines = text.strip().split('\n')

    # First line as subject, rest as description
    subject = lines[0][:200] if lines else "Laporan via WhatsApp"
    description = '\n'.join(lines[1:]) if len(lines) > 1 else lines[0]

    return {
        "subject": subject,
        "description": description
    }


def parse_email_report(subject: str, body: str) -> Dict[str, str]:
    """Parse report from email content."""
    # Clean subject
    clean_subject = re.sub(r'^(Re:|Fwd:|FW:)\s*', '', subject, flags=re.IGNORECASE).strip()

    return {
        "subject": clean_subject[:200] if clean_subject else "Laporan via Email",
        "description": body
    }


# ============== WhatsApp Webhook ==============

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive incoming WhatsApp messages from WAHA.

    Message format from reporter:
    - "LAPOR: <description>" - Create new report
    - "STATUS <ticket_id>" - Check report status
    - "<ticket_id> <message>" - Send message to existing report
    """
    try:
        body = await request.json()
        logger.info(f"WhatsApp webhook received: {body.get('event', 'unknown')}")

        event = body.get("event")

        # Only process incoming messages
        if event != "message":
            return {"status": "ignored", "reason": f"Event type: {event}"}

        payload = body.get("payload", {})
        message_body = payload.get("body", "").strip()
        from_number = payload.get("from", "").replace("@c.us", "")

        if not message_body:
            return {"status": "ignored", "reason": "Empty message"}

        message_upper = message_body.upper()

        # Command: Create new report
        if message_upper.startswith("LAPOR:") or message_upper.startswith("LAPOR "):
            report_text = message_body[6:].strip()  # Remove "LAPOR:" prefix

            if len(report_text) < 20:
                # Too short, send help
                await notification_service.whatsapp.send_message(
                    from_number,
                    """Untuk membuat laporan, kirim pesan dengan format:

LAPOR: [Deskripsi lengkap pelanggaran]

Contoh:
LAPOR: Saya menemukan dugaan penyalahgunaan dana pada kegiatan X di unit Y pada tanggal Z.

Sertakan detail: Apa, Siapa, Kapan, Dimana, dan Bagaimana."""
                )
                return {"status": "help_sent"}

            # Parse and create report
            parsed = parse_report_from_text(report_text)

            report = await report_repo.create({
                "subject": parsed["subject"],
                "description": parsed["description"],
                "category": "LAINNYA",
                "reporter_contact": from_number,
                "source_channel": "WHATSAPP"
            })

            # Send confirmation
            await notification_service.whatsapp.send_report_confirmation(
                from_number,
                report["ticket_id"]
            )

            logger.info(f"Report created via WhatsApp: {report['ticket_id']}")
            return {"status": "report_created", "ticket_id": report["ticket_id"]}

        # Command: Check status
        elif message_upper.startswith("STATUS"):
            ticket_id = extract_ticket_from_message(message_body)

            if not ticket_id:
                await notification_service.whatsapp.send_message(
                    from_number,
                    """Untuk cek status, kirim:
STATUS <ID Tiket>

Contoh:
STATUS A1B2C3D4"""
                )
                return {"status": "help_sent"}

            # Find report
            report = await report_repo.get_by_ticket_id(ticket_id)

            if not report:
                await notification_service.whatsapp.send_message(
                    from_number,
                    f"Laporan dengan ID Tiket {ticket_id} tidak ditemukan."
                )
                return {"status": "not_found"}

            status_labels = {
                "SUBMITTED": "Diterima",
                "UNDER_REVIEW": "Sedang Ditinjau",
                "INVESTIGATION": "Dalam Investigasi",
                "ACTION_TAKEN": "Tindakan Diambil",
                "RESOLVED": "Selesai",
                "DISMISSED": "Ditutup"
            }

            status_label = status_labels.get(report["status"], report["status"])

            await notification_service.whatsapp.send_message(
                from_number,
                f"""*Status Laporan*
ID Tiket: {ticket_id}
Status: *{status_label}*
Tanggal Lapor: {report['created_at'][:10]}

Untuk detail lengkap, kunjungi:
https://wbs-bpkh.up.railway.app"""
            )
            return {"status": "status_sent"}

        # Try to match existing ticket and send message
        else:
            ticket_id = extract_ticket_from_message(message_body)

            if ticket_id:
                report = await report_repo.get_by_ticket_id(ticket_id)

                if report:
                    # Remove ticket ID from message
                    clean_message = re.sub(r'\b[A-F0-9]{8}\b', '', message_body, flags=re.IGNORECASE).strip()

                    if clean_message:
                        # Save message
                        await message_repo.create({
                            "ticket_id": ticket_id,
                            "report_id": report["id"],
                            "sender_type": "REPORTER",
                            "content": clean_message,
                            "is_from_admin": False
                        })

                        await notification_service.whatsapp.send_message(
                            from_number,
                            f"Pesan Anda untuk tiket {ticket_id} telah terkirim."
                        )
                        return {"status": "message_sent"}

            # Unknown command, send help
            await notification_service.whatsapp.send_message(
                from_number,
                """*WBS BPKH - Whistleblowing System*

Perintah yang tersedia:

*LAPOR: [deskripsi]*
Buat laporan baru

*STATUS [ID Tiket]*
Cek status laporan

*[ID Tiket] [pesan]*
Kirim pesan untuk laporan tertentu

Contoh:
LAPOR: Saya menemukan dugaan korupsi...
STATUS A1B2C3D4
A1B2C3D4 Ada informasi tambahan..."""
            )
            return {"status": "help_sent"}

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ============== Email Webhook ==============

@router.post("/email")
async def email_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive incoming emails from email-to-webhook service.

    Subject patterns:
    - "[LAPOR] <subject>" - Create new report
    - "Re: [WBS BPKH] ... Tiket #<ticket_id>" - Reply to existing report
    """
    try:
        body = await request.json()
        logger.info(f"Email webhook received from: {body.get('from', 'unknown')}")

        from_email = body.get("from", "")
        subject = body.get("subject", "")
        body_text = body.get("body_text", body.get("text", ""))

        if not body_text:
            return {"status": "ignored", "reason": "Empty body"}

        subject_upper = subject.upper()

        # New report: [LAPOR] prefix
        if subject_upper.startswith("[LAPOR]") or subject_upper.startswith("LAPOR:"):
            parsed = parse_email_report(subject, body_text)

            report = await report_repo.create({
                "subject": parsed["subject"].replace("[LAPOR]", "").replace("[lapor]", "").strip(),
                "description": parsed["description"],
                "category": "LAINNYA",
                "reporter_contact": from_email,
                "source_channel": "EMAIL"
            })

            # Send confirmation
            await notification_service.email.send_report_confirmation(
                from_email,
                report["ticket_id"]
            )

            logger.info(f"Report created via Email: {report['ticket_id']}")
            return {"status": "report_created", "ticket_id": report["ticket_id"]}

        # Reply to existing report
        ticket_id = extract_ticket_from_message(subject)

        if ticket_id:
            report = await report_repo.get_by_ticket_id(ticket_id)

            if report:
                # Clean the reply (remove quoted text)
                clean_body = body_text.split("---")[0].strip()  # Remove footer
                clean_body = re.split(r'\n>|\nOn .* wrote:', clean_body)[0].strip()  # Remove quoted

                if clean_body:
                    await message_repo.create({
                        "ticket_id": ticket_id,
                        "report_id": report["id"],
                        "sender_type": "REPORTER",
                        "content": clean_body,
                        "is_from_admin": False
                    })

                    logger.info(f"Message added to report {ticket_id} via email")
                    return {"status": "message_added", "ticket_id": ticket_id}

        # Unknown format, create as new report
        parsed = parse_email_report(subject, body_text)

        report = await report_repo.create({
            "subject": parsed["subject"],
            "description": parsed["description"],
            "category": "LAINNYA",
            "reporter_contact": from_email,
            "source_channel": "EMAIL"
        })

        await notification_service.email.send_report_confirmation(
            from_email,
            report["ticket_id"]
        )

        logger.info(f"Report created via Email (fallback): {report['ticket_id']}")
        return {"status": "report_created", "ticket_id": report["ticket_id"]}

    except Exception as e:
        logger.error(f"Email webhook error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ============== Channel Status ==============

@router.get("/status")
async def get_channel_status():
    """Get status of notification channels."""
    return {
        "channels": notification_service.get_status(),
        "available": notification_service.get_available_channels()
    }
