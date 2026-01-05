"""
WBS BPKH AI - Email Service (SMTP Integration)
===============================================
Handles email sending/receiving via SMTP.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, Dict, Any, List
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import settings


class EmailService:
    """Service for email integration using SMTP."""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.wbs_email = settings.wbs_email
        self.enabled = bool(self.smtp_host and self.smtp_user and self.smtp_password)
        self._executor = ThreadPoolExecutor(max_workers=2)

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self.enabled

    def _create_message(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email message."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr(("WBS BPKH", self.wbs_email))
        msg["To"] = to

        # Plain text version
        part1 = MIMEText(body_text, "plain", "utf-8")
        msg.attach(part1)

        # HTML version (if provided)
        if body_html:
            part2 = MIMEText(body_html, "html", "utf-8")
            msg.attach(part2)

        return msg

    def _send_sync(self, to: str, subject: str, body_text: str, body_html: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous email send (runs in thread pool)."""
        try:
            msg = self._create_message(to, subject, body_text, body_html)

            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.wbs_email, to, msg.as_string())

            logger.info(f"Email sent to {to[:5]}***")
            return {"success": True}

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {"success": False, "error": str(e)}

    async def send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email asynchronously.

        Args:
            to: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body

        Returns:
            Response dict with success status
        """
        if not self.is_configured():
            logger.warning("Email service not configured, skipping send")
            return {"success": False, "error": "Email not configured"}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._send_sync,
            to, subject, body_text, body_html
        )

    async def send_report_confirmation(
        self,
        to: str,
        ticket_id: str
    ) -> Dict[str, Any]:
        """Send report submission confirmation email."""
        subject = f"[WBS BPKH] Laporan Diterima - Tiket #{ticket_id}"

        body_text = f"""Assalamu'alaikum Wr. Wb.

Laporan Anda telah kami terima.

ID Tiket: {ticket_id}

Simpan ID tiket ini untuk memantau status laporan Anda di:
https://wbs-bpkh.up.railway.app

Kami akan memproses laporan Anda sesuai prosedur yang berlaku.
Identitas Anda dijamin kerahasiaannya.

Wassalamu'alaikum Wr. Wb.
Tim WBS BPKH

---
Email ini dikirim secara otomatis. Mohon tidak membalas email ini.
Untuk komunikasi lebih lanjut, gunakan portal WBS BPKH."""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #006B3F, #004d2e); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .ticket-box {{ background: #fff; border: 2px solid #C9A227; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
        .ticket-id {{ font-size: 28px; font-weight: bold; color: #006B3F; letter-spacing: 2px; }}
        .btn {{ display: inline-block; background: #006B3F; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .bismillah {{ text-align: center; color: #C9A227; font-size: 18px; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="bismillah">&#1576;&#1587;&#1605; &#1575;&#1604;&#1604;&#1607; &#1575;&#1604;&#1585;&#1581;&#1605;&#1606; &#1575;&#1604;&#1585;&#1581;&#1610;&#1605;</div>
            <h1>Whistleblowing System BPKH</h1>
        </div>
        <div class="content">
            <p>Assalamu'alaikum Wr. Wb.</p>
            <p>Laporan Anda telah kami terima dan akan diproses sesuai prosedur yang berlaku.</p>

            <div class="ticket-box">
                <p>ID Tiket Anda:</p>
                <div class="ticket-id">{ticket_id}</div>
                <p style="color: #666; font-size: 12px;">Simpan ID ini untuk memantau status laporan</p>
            </div>

            <p style="text-align: center;">
                <a href="https://wbs-bpkh.up.railway.app" class="btn">Pantau Status Laporan</a>
            </p>

            <p><strong>Kerahasiaan Terjamin</strong><br>
            Identitas Anda dijamin kerahasiaannya sesuai dengan ketentuan yang berlaku.</p>

            <p>Wassalamu'alaikum Wr. Wb.<br>
            <strong>Tim WBS BPKH</strong></p>
        </div>
        <div class="footer">
            <p>Email ini dikirim secara otomatis. Mohon tidak membalas email ini.<br>
            Untuk komunikasi lebih lanjut, gunakan portal WBS BPKH.</p>
            <p>&copy; 2025 Badan Pengelola Keuangan Haji</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email(to, subject, body_text, body_html)

    async def send_status_update(
        self,
        to: str,
        ticket_id: str,
        old_status: str,
        new_status: str,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send status update notification email."""
        status_labels = {
            "SUBMITTED": "Diterima",
            "UNDER_REVIEW": "Sedang Ditinjau",
            "INVESTIGATION": "Dalam Investigasi",
            "ACTION_TAKEN": "Tindakan Diambil",
            "RESOLVED": "Selesai",
            "DISMISSED": "Ditutup"
        }

        new_label = status_labels.get(new_status, new_status)
        subject = f"[WBS BPKH] Update Status - Tiket #{ticket_id}"

        note_text = f"\n\nCatatan:\n{note}" if note else ""

        body_text = f"""Assalamu'alaikum Wr. Wb.

Update Status Laporan
ID Tiket: {ticket_id}

Status baru: {new_label}{note_text}

Pantau perkembangan di:
https://wbs-bpkh.up.railway.app

Wassalamu'alaikum Wr. Wb.
Tim WBS BPKH

---
Email ini dikirim secara otomatis. Mohon tidak membalas email ini."""

        note_html = f'<div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #C9A227; margin: 15px 0;"><strong>Catatan:</strong><br>{note}</div>' if note else ""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #006B3F, #004d2e); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .status-box {{ background: #fff; border: 2px solid #006B3F; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
        .status {{ font-size: 24px; font-weight: bold; color: #006B3F; }}
        .ticket {{ color: #666; }}
        .btn {{ display: inline-block; background: #006B3F; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Update Status Laporan</h1>
        </div>
        <div class="content">
            <p>Assalamu'alaikum Wr. Wb.</p>

            <div class="status-box">
                <p class="ticket">ID Tiket: <strong>{ticket_id}</strong></p>
                <p>Status baru:</p>
                <div class="status">{new_label}</div>
            </div>

            {note_html}

            <p style="text-align: center;">
                <a href="https://wbs-bpkh.up.railway.app" class="btn">Lihat Detail</a>
            </p>

            <p>Wassalamu'alaikum Wr. Wb.<br>
            <strong>Tim WBS BPKH</strong></p>
        </div>
        <div class="footer">
            <p>Email ini dikirim secara otomatis. Mohon tidak membalas email ini.</p>
            <p>&copy; 2025 Badan Pengelola Keuangan Haji</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email(to, subject, body_text, body_html)

    async def send_new_message_notification(
        self,
        to: str,
        ticket_id: str
    ) -> Dict[str, Any]:
        """Notify reporter about new admin message."""
        subject = f"[WBS BPKH] Pesan Baru - Tiket #{ticket_id}"

        body_text = f"""Assalamu'alaikum Wr. Wb.

Ada pesan baru untuk laporan Anda.

ID Tiket: {ticket_id}

Silakan cek pesan di:
https://wbs-bpkh.up.railway.app

Wassalamu'alaikum Wr. Wb.
Tim WBS BPKH

---
Email ini dikirim secara otomatis. Mohon tidak membalas email ini."""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #006B3F, #004d2e); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .message-icon {{ font-size: 48px; text-align: center; margin: 20px 0; }}
        .btn {{ display: inline-block; background: #006B3F; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Pesan Baru</h1>
        </div>
        <div class="content">
            <p>Assalamu'alaikum Wr. Wb.</p>

            <div class="message-icon">&#128172;</div>

            <p style="text-align: center;">Ada pesan baru untuk laporan Anda.<br>
            <strong>ID Tiket: {ticket_id}</strong></p>

            <p style="text-align: center;">
                <a href="https://wbs-bpkh.up.railway.app" class="btn">Buka Pesan</a>
            </p>

            <p>Wassalamu'alaikum Wr. Wb.<br>
            <strong>Tim WBS BPKH</strong></p>
        </div>
        <div class="footer">
            <p>Email ini dikirim secara otomatis. Mohon tidak membalas email ini.</p>
            <p>&copy; 2025 Badan Pengelola Keuangan Haji</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email(to, subject, body_text, body_html)


# Global instance
email_service = EmailService()
