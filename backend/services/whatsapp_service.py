"""
WBS BPKH AI - WhatsApp Service (WAHA Integration)
=================================================
Handles WhatsApp message sending/receiving via WAHA API.
"""

import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
from datetime import datetime

from config import settings


class WhatsAppService:
    """Service for WhatsApp integration using WAHA (WhatsApp HTTP API)."""

    def __init__(self):
        self.api_url = settings.waha_api_url
        self.session = settings.waha_session
        self.primary_number = settings.waha_number_primary
        self.backup_number = settings.waha_number_backup
        self.enabled = bool(self.api_url)

    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured."""
        return self.enabled and bool(self.api_url)

    def _format_phone(self, phone: str) -> str:
        """Format phone number for WhatsApp (remove +, spaces, etc.)."""
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone))
        # Ensure it starts with country code
        if cleaned.startswith('0'):
            cleaned = '62' + cleaned[1:]  # Indonesia
        return cleaned + '@c.us'

    async def send_message(
        self,
        to: str,
        message: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp text message.

        Args:
            to: Recipient phone number
            message: Message text
            reply_to: Optional message ID to reply to

        Returns:
            Response from WAHA API
        """
        if not self.is_configured():
            logger.warning("WhatsApp service not configured, skipping send")
            return {"success": False, "error": "WhatsApp not configured"}

        try:
            chat_id = self._format_phone(to)

            payload = {
                "chatId": chat_id,
                "text": message,
                "session": self.session
            }

            if reply_to:
                payload["reply_to"] = reply_to

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/sendText",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                logger.info(f"WhatsApp message sent to {to[:8]}***")
                return {"success": True, "data": result}

        except httpx.HTTPError as e:
            logger.error(f"WhatsApp send error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return {"success": False, "error": str(e)}

    async def send_report_confirmation(
        self,
        to: str,
        ticket_id: str
    ) -> Dict[str, Any]:
        """Send report submission confirmation."""
        message = f"""Assalamu'alaikum Wr. Wb.

Laporan Anda telah kami terima.

*ID Tiket: {ticket_id}*

Simpan ID tiket ini untuk memantau status laporan Anda di:
https://wbs-bpkh.up.railway.app

Kami akan memproses laporan Anda sesuai prosedur yang berlaku. Identitas Anda dijamin kerahasiaannya.

Wassalamu'alaikum Wr. Wb.
_Tim WBS BPKH_"""

        return await self.send_message(to, message)

    async def send_status_update(
        self,
        to: str,
        ticket_id: str,
        old_status: str,
        new_status: str,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send status update notification."""
        status_labels = {
            "SUBMITTED": "Diterima",
            "UNDER_REVIEW": "Sedang Ditinjau",
            "INVESTIGATION": "Dalam Investigasi",
            "ACTION_TAKEN": "Tindakan Diambil",
            "RESOLVED": "Selesai",
            "DISMISSED": "Ditutup"
        }

        new_label = status_labels.get(new_status, new_status)

        message = f"""Assalamu'alaikum Wr. Wb.

*Update Status Laporan*
ID Tiket: {ticket_id}

Status baru: *{new_label}*"""

        if note:
            message += f"\n\nCatatan:\n{note}"

        message += f"""

Pantau perkembangan di:
https://wbs-bpkh.up.railway.app

_Tim WBS BPKH_"""

        return await self.send_message(to, message)

    async def send_new_message_notification(
        self,
        to: str,
        ticket_id: str
    ) -> Dict[str, Any]:
        """Notify reporter about new admin message."""
        message = f"""Assalamu'alaikum Wr. Wb.

Ada pesan baru untuk laporan Anda.

ID Tiket: {ticket_id}

Silakan cek pesan di:
https://wbs-bpkh.up.railway.app

_Tim WBS BPKH_"""

        return await self.send_message(to, message)

    async def check_session_status(self) -> Dict[str, Any]:
        """Check WAHA session status."""
        if not self.is_configured():
            return {"status": "not_configured"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/api/sessions/{self.session}"
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"WhatsApp session check error: {e}")
            return {"status": "error", "error": str(e)}


# Global instance
whatsapp_service = WhatsAppService()
