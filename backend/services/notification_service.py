"""
WBS BPKH AI - Notification Service
===================================
Coordinates notifications via WhatsApp and Email channels.
"""

from typing import Optional, Dict, Any, List
from loguru import logger
from enum import Enum

from .whatsapp_service import whatsapp_service
from .email_service import email_service


class NotificationChannel(str, Enum):
    """Available notification channels."""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    BOTH = "both"


class NotificationService:
    """
    Unified notification service that handles sending notifications
    through multiple channels (WhatsApp, Email).
    """

    def __init__(self):
        self.whatsapp = whatsapp_service
        self.email = email_service

    def get_available_channels(self) -> List[str]:
        """Get list of configured notification channels."""
        channels = []
        if self.whatsapp.is_configured():
            channels.append("whatsapp")
        if self.email.is_configured():
            channels.append("email")
        return channels

    def get_status(self) -> Dict[str, Any]:
        """Get status of all notification channels."""
        return {
            "whatsapp": {
                "configured": self.whatsapp.is_configured(),
                "primary_number": self.whatsapp.primary_number if self.whatsapp.is_configured() else None,
                "backup_number": self.whatsapp.backup_number if self.whatsapp.is_configured() else None,
            },
            "email": {
                "configured": self.email.is_configured(),
                "wbs_email": self.email.wbs_email if self.email.is_configured() else None,
            }
        }

    async def send_report_confirmation(
        self,
        ticket_id: str,
        reporter_phone: Optional[str] = None,
        reporter_email: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.BOTH
    ) -> Dict[str, Any]:
        """
        Send report submission confirmation via configured channels.

        Args:
            ticket_id: The report ticket ID
            reporter_phone: Reporter's phone number (for WhatsApp)
            reporter_email: Reporter's email address
            channel: Which channel(s) to use

        Returns:
            Result dict with status for each channel
        """
        results = {
            "whatsapp": None,
            "email": None
        }

        # Send via WhatsApp
        if reporter_phone and channel in [NotificationChannel.WHATSAPP, NotificationChannel.BOTH]:
            if self.whatsapp.is_configured():
                results["whatsapp"] = await self.whatsapp.send_report_confirmation(
                    to=reporter_phone,
                    ticket_id=ticket_id
                )
            else:
                results["whatsapp"] = {"success": False, "error": "WhatsApp not configured"}

        # Send via Email
        if reporter_email and channel in [NotificationChannel.EMAIL, NotificationChannel.BOTH]:
            if self.email.is_configured():
                results["email"] = await self.email.send_report_confirmation(
                    to=reporter_email,
                    ticket_id=ticket_id
                )
            else:
                results["email"] = {"success": False, "error": "Email not configured"}

        logger.info(f"Report confirmation sent for ticket {ticket_id}: WA={results['whatsapp']}, Email={results['email']}")
        return results

    async def send_status_update(
        self,
        ticket_id: str,
        old_status: str,
        new_status: str,
        reporter_phone: Optional[str] = None,
        reporter_email: Optional[str] = None,
        note: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.BOTH
    ) -> Dict[str, Any]:
        """
        Send status update notification via configured channels.

        Args:
            ticket_id: The report ticket ID
            old_status: Previous status
            new_status: New status
            reporter_phone: Reporter's phone number
            reporter_email: Reporter's email address
            note: Optional note to include
            channel: Which channel(s) to use

        Returns:
            Result dict with status for each channel
        """
        results = {
            "whatsapp": None,
            "email": None
        }

        # Send via WhatsApp
        if reporter_phone and channel in [NotificationChannel.WHATSAPP, NotificationChannel.BOTH]:
            if self.whatsapp.is_configured():
                results["whatsapp"] = await self.whatsapp.send_status_update(
                    to=reporter_phone,
                    ticket_id=ticket_id,
                    old_status=old_status,
                    new_status=new_status,
                    note=note
                )
            else:
                results["whatsapp"] = {"success": False, "error": "WhatsApp not configured"}

        # Send via Email
        if reporter_email and channel in [NotificationChannel.EMAIL, NotificationChannel.BOTH]:
            if self.email.is_configured():
                results["email"] = await self.email.send_status_update(
                    to=reporter_email,
                    ticket_id=ticket_id,
                    old_status=old_status,
                    new_status=new_status,
                    note=note
                )
            else:
                results["email"] = {"success": False, "error": "Email not configured"}

        logger.info(f"Status update sent for ticket {ticket_id}: {old_status} -> {new_status}")
        return results

    async def send_new_message_notification(
        self,
        ticket_id: str,
        reporter_phone: Optional[str] = None,
        reporter_email: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.BOTH
    ) -> Dict[str, Any]:
        """
        Notify reporter about new admin message.

        Args:
            ticket_id: The report ticket ID
            reporter_phone: Reporter's phone number
            reporter_email: Reporter's email address
            channel: Which channel(s) to use

        Returns:
            Result dict with status for each channel
        """
        results = {
            "whatsapp": None,
            "email": None
        }

        # Send via WhatsApp
        if reporter_phone and channel in [NotificationChannel.WHATSAPP, NotificationChannel.BOTH]:
            if self.whatsapp.is_configured():
                results["whatsapp"] = await self.whatsapp.send_new_message_notification(
                    to=reporter_phone,
                    ticket_id=ticket_id
                )
            else:
                results["whatsapp"] = {"success": False, "error": "WhatsApp not configured"}

        # Send via Email
        if reporter_email and channel in [NotificationChannel.EMAIL, NotificationChannel.BOTH]:
            if self.email.is_configured():
                results["email"] = await self.email.send_new_message_notification(
                    to=reporter_email,
                    ticket_id=ticket_id
                )
            else:
                results["email"] = {"success": False, "error": "Email not configured"}

        logger.info(f"New message notification sent for ticket {ticket_id}")
        return results


# Global instance
notification_service = NotificationService()
