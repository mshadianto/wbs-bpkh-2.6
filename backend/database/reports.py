"""
WBS BPKH AI - Report Repository
================================
CRUD operations for whistleblowing reports.
"""

import uuid
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from config import SEVERITY_LEVELS
from .client import SupabaseDB
from .utils import (
    sanitize_input, sanitize_list, sanitize_search_query,
    validate_field_length, parse_date_safe,
)


class ReportRepository:
    """Repository for Report operations."""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "reports"

    def generate_ticket_id(self) -> str:
        """Generate unique 8-character ticket ID."""
        return uuid.uuid4().hex[:8].upper()

    async def create(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new report."""
        ticket_id = self.generate_ticket_id()

        record = {
            "id": str(uuid.uuid4()),
            "ticket_id": ticket_id,
            "channel": report_data.get("channel", "WEB"),
            "is_anonymous": report_data.get("is_anonymous", True),
            "title": sanitize_input(validate_field_length(report_data.get("subject", ""), "title")),
            "description": sanitize_input(validate_field_length(report_data.get("description", ""), "description")),
            "incident_date": parse_date_safe(report_data.get("incident_date")),
            "incident_location": sanitize_input(validate_field_length(report_data.get("incident_location") or "", "incident_location")),
            "involved_parties": sanitize_list(report_data.get("parties_involved", [])),
            "reporter_email": sanitize_input(validate_field_length(report_data.get("reporter_contact") or "", "reporter_email")),
            "status": "NEW",
            "severity": None,
            "category": report_data.get("category") or None,
            "fraud_score": None,
            "ai_analysis": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = self.db.table(self.table).insert(record).execute()
        logger.info(f"Created report with ticket_id: {ticket_id}")

        # Save attachments to attachments table
        attachment_ids = report_data.get("attachments") or []
        if attachment_ids:
            await self._link_attachments(record["id"], attachment_ids)

        await self._create_audit_log(
            record["id"], "REPORT_CREATED",
            {"ticket_id": ticket_id, "channel": record["channel"]},
        )

        return result.data[0] if result.data else record

    async def get_by_ticket_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get report by ticket ID."""
        result = self.db.table(self.table)\
            .select("*").eq("ticket_id", ticket_id.upper()).execute()
        return result.data[0] if result.data else None

    async def get_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report by ID."""
        result = self.db.table(self.table)\
            .select("*").eq("id", report_id).execute()
        return result.data[0] if result.data else None

    async def update_status(
        self, report_id: str, new_status: str, updated_by: str = "SYSTEM",
    ) -> Dict[str, Any]:
        """Update report status."""
        result = self.db.table(self.table).update({
            "status": new_status,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", report_id).execute()

        await self._create_audit_log(
            report_id, "STATUS_CHANGED",
            {"new_status": new_status, "updated_by": updated_by},
        )
        return result.data[0] if result.data else None

    async def update_analysis(
        self, report_id: str, analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update AI analysis results and calculate SLA deadlines."""
        update_data = {
            "severity": analysis.get("severity"),
            "category": analysis.get("category"),
            "fraud_score": analysis.get("fraud_score"),
            "ai_analysis": analysis,
            "updated_at": datetime.utcnow().isoformat(),
        }

        severity = analysis.get("severity", "MEDIUM")
        sla_config = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["MEDIUM"])

        report = await self.get_by_id(report_id)
        if report:
            if report.get("status", "NEW") == "NEW":
                update_data["status"] = "REVIEWING"

            created_at = report.get("created_at", datetime.utcnow().isoformat())
            try:
                if isinstance(created_at, str):
                    base_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    base_time = created_at
            except (ValueError, TypeError):
                base_time = datetime.utcnow()

            update_data["sla_response_deadline"] = (
                base_time + timedelta(hours=sla_config["sla_initial_hours"])
            ).isoformat()
            update_data["sla_review_deadline"] = (
                base_time + timedelta(hours=sla_config["sla_investigation_hours"])
            ).isoformat()
            update_data["sla_investigation_deadline"] = (
                base_time + timedelta(days=sla_config["sla_resolution_days"])
            ).isoformat()

        result = self.db.table(self.table).update(update_data)\
            .eq("id", report_id).execute()

        await self._create_audit_log(
            report_id, "AI_ANALYSIS_COMPLETED",
            {"severity": analysis.get("severity"), "fraud_score": analysis.get("fraud_score")},
        )
        return result.data[0] if result.data else None

    async def get_sla_at_risk_count(self) -> int:
        """Count reports where SLA deadline is approaching (within 24h) or breached."""
        upcoming = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        closed_statuses = ["CLOSED_PROVEN", "CLOSED_NOT_PROVEN", "CLOSED_INVALID"]
        try:
            result = self.db.table(self.table)\
                .select("id", count="exact")\
                .not_.in_("status", closed_statuses)\
                .lte("sla_investigation_deadline", upcoming)\
                .execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error(f"Failed to get SLA at risk count: {e}")
            return 0

    async def list_all(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        assigned_to: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List reports with filters."""
        query = self.db.table(self.table).select("*")

        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)
        if category:
            query = query.eq("category", category)
        if assigned_to:
            query = query.eq("assigned_to", assigned_to)
        if date_from:
            safe_date = parse_date_safe(date_from)
            if safe_date:
                query = query.gte("created_at", safe_date)
        if date_to:
            safe_date = parse_date_safe(date_to)
            if safe_date:
                query = query.lte("created_at", safe_date)
        if search:
            safe_search = sanitize_search_query(search)
            if safe_search:
                query = query.or_(
                    f"title.ilike.%{safe_search}%,"
                    f"description.ilike.%{safe_search}%,"
                    f"ticket_id.ilike.%{safe_search}%"
                )

        allowed_sort = {"created_at", "severity", "status", "category", "ticket_id", "fraud_score"}
        sort_field = sort_by if sort_by in allowed_sort else "created_at"
        query = query.order(sort_field, desc=sort_order.lower() == "desc")\
            .range(offset, offset + limit - 1)

        result = query.execute()
        return result.data or []

    async def get_total_count(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> int:
        """Get total count of reports matching filters."""
        query = self.db.table(self.table).select("id", count="exact")

        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)
        if category:
            query = query.eq("category", category)
        if assigned_to:
            query = query.eq("assigned_to", assigned_to)
        if date_from:
            safe_date = parse_date_safe(date_from)
            if safe_date:
                query = query.gte("created_at", safe_date)
        if date_to:
            safe_date = parse_date_safe(date_to)
            if safe_date:
                query = query.lte("created_at", safe_date)
        if search:
            safe_search = sanitize_search_query(search)
            if safe_search:
                query = query.or_(
                    f"title.ilike.%{safe_search}%,"
                    f"description.ilike.%{safe_search}%,"
                    f"ticket_id.ilike.%{safe_search}%"
                )

        result = query.execute()
        return result.count if result.count is not None else len(result.data or [])

    async def get_statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        all_reports = self.db.table(self.table)\
            .select("status, severity, category, created_at").execute()

        stats = {
            "total": len(all_reports.data) if all_reports.data else 0,
            "by_status": {},
            "by_severity": {},
            "by_category": {},
            "active_investigations": 0,
            "closure_rate": 0.0,
            "recent_reports_7d": 0,
        }

        closed_count = 0
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        for report in (all_reports.data or []):
            s = report.get("status") or "UNKNOWN"
            sev = report.get("severity") or "UNASSIGNED"
            cat = report.get("category") or "UNASSIGNED"

            stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            if s in ("INVESTIGATING", "ESCALATED"):
                stats["active_investigations"] += 1
            if s.startswith("CLOSED"):
                closed_count += 1
            if report.get("created_at", "") >= seven_days_ago:
                stats["recent_reports_7d"] += 1

        if stats["total"] > 0:
            stats["closure_rate"] = round(closed_count / stats["total"] * 100, 1)

        return stats

    async def _link_attachments(
        self, report_id: str, file_ids: List[str],
        message_id: str = None,
    ):
        """Link uploaded files to a report (and optionally a message)."""
        db = self.db
        for file_id in file_ids:
            try:
                # Try to find the file in Supabase Storage to get metadata
                storage_path = None
                original_filename = file_id
                file_size = None
                mime_type = None

                # Look for file by ID prefix in storage
                try:
                    files_list = db.storage.from_("attachments").list()
                    for f in (files_list or []):
                        name = f.get("name", "")
                        if name.startswith(file_id):
                            storage_path = name
                            original_filename = name
                            file_size = f.get("metadata", {}).get("size")
                            mime_type = f.get("metadata", {}).get("mimetype")
                            break
                except Exception:
                    storage_path = file_id

                import os
                ext = os.path.splitext(storage_path or file_id)[1] if storage_path else ""

                record = {
                    "id": str(uuid.uuid4()),
                    "report_id": report_id,
                    "message_id": message_id,
                    "filename": storage_path or file_id,
                    "original_filename": original_filename,
                    "file_type": ext.lstrip(".") if ext else None,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "storage_path": storage_path,
                    "storage_bucket": "attachments",
                    "uploaded_at": datetime.utcnow().isoformat(),
                }
                db.table("attachments").insert(record).execute()
                logger.info(f"Linked attachment {file_id} to report {report_id}")
            except Exception as e:
                logger.error(f"Failed to link attachment {file_id}: {e}")

    async def get_attachments(self, report_id: str) -> List[Dict[str, Any]]:
        """Get all attachments for a report."""
        try:
            result = self.db.table("attachments")\
                .select("*").eq("report_id", report_id)\
                .order("uploaded_at", desc=False).execute()
            attachments = result.data or []

            # Generate signed URLs for download
            for att in attachments:
                if att.get("storage_path"):
                    try:
                        signed = self.db.storage.from_("attachments")\
                            .create_signed_url(att["storage_path"], 3600)
                        att["download_url"] = signed.get("signedURL") or signed.get("signedUrl", "")
                    except Exception:
                        att["download_url"] = ""
            return attachments
        except Exception as e:
            logger.error(f"Failed to get attachments: {e}")
            return []

    async def _create_audit_log(
        self, report_id: str, action: str, details: Dict[str, Any],
    ):
        """Create audit trail entry."""
        try:
            self.db.table("audit_logs").insert({
                "id": str(uuid.uuid4()),
                "entity_type": "report",
                "entity_id": report_id,
                "action": action,
                "action_details": json.dumps(details) if isinstance(details, dict) else str(details),
                "actor_type": details.get("actor_type", "SYSTEM") if isinstance(details, dict) else "SYSTEM",
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

    async def get_audit_logs(
        self,
        report_id: Optional[str] = None,
        action: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get audit logs with filtering."""
        query = self.db.table("audit_logs").select("*", count="exact")

        if report_id:
            query = query.eq("entity_id", report_id).eq("entity_type", "report")
        if action:
            query = query.eq("action", action)
        if date_from:
            safe_date = parse_date_safe(date_from)
            if safe_date:
                query = query.gte("created_at", safe_date)
        if date_to:
            safe_date = parse_date_safe(date_to)
            if safe_date:
                query = query.lte("created_at", safe_date)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        return {"logs": result.data or [], "total": result.count or 0}
