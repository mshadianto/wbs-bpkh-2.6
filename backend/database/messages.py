"""
WBS BPKH AI - Message Repository
=================================
CRUD operations for report messages/communication.
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from .client import SupabaseDB
from .utils import sanitize_input, validate_field_length


class MessageRepository:
    """Repository for Message/Communication operations."""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "messages"

    async def create(
        self,
        report_id: str,
        content: str,
        sender_type: str = "REPORTER",
        attachments: List[str] = None,
        ticket_id: str = None,
    ) -> Dict[str, Any]:
        """Create new message."""
        record = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "ticket_id": ticket_id,
            "content": sanitize_input(validate_field_length(content, "content")),
            "sender_type": sender_type,
            "has_attachments": bool(attachments),
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        result = self.db.table(self.table).insert(record).execute()
        return result.data[0] if result.data else record

    async def get_by_report(self, report_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a report."""
        result = self.db.table(self.table)\
            .select("*").eq("report_id", report_id)\
            .order("created_at", desc=False).execute()
        return result.data or []

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark message as read."""
        result = self.db.table(self.table)\
            .update({"is_read": True}).eq("id", message_id).execute()
        return result.data[0] if result.data else None
