"""
WBS BPKH AI - Database Module
============================
Supabase database client and operations.
"""

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
import uuid
import json
import re
from loguru import logger

from config import settings
import html


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS attacks.
    Removes HTML tags and escapes special characters.
    """
    if not text:
        return text

    # Remove script tags and content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove other potentially dangerous tags
    text = re.sub(r'<(iframe|object|embed|link|style|img\s+[^>]*onerror)[^>]*>.*?</\1>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove event handlers
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)

    # Escape HTML entities
    text = html.escape(text)

    return text


def sanitize_list(items: List[str]) -> List[str]:
    """Sanitize a list of strings."""
    if not items:
        return items
    return [sanitize_input(item) for item in items]


def sanitize_search_query(search: str) -> str:
    """
    Sanitize search query for use in PostgREST ilike filters.
    Escapes characters that could break filter syntax or enable injection.
    """
    if not search:
        return search
    # Remove PostgREST special characters that could break or_/ilike syntax
    # Commas separate filter conditions, dots separate field.operator.value
    sanitized = re.sub(r'[,.()\[\]{}\\;\'"]', '', search)
    # Limit length to prevent abuse
    return sanitized[:200].strip()


def parse_date_safe(date_str: str) -> str | None:
    """
    Safely parse date string to ISO format.
    Handles various formats: YYYY-MM-DD, YYYY-MM, YYYY, etc.
    Returns None if invalid.
    """
    if not date_str or date_str in ["Unknown", "Tidak disebutkan", "N/A", "-"]:
        return None

    date_str = str(date_str).strip()

    # Try exact date format YYYY-MM-DD
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.date().isoformat()
    except ValueError:
        pass

    # Try YYYY-MM format -> default to first day
    try:
        parsed = datetime.strptime(date_str, "%Y-%m")
        return parsed.date().isoformat()
    except ValueError:
        pass

    # Try just year YYYY -> default to Jan 1
    if re.match(r"^\d{4}$", date_str):
        try:
            year = int(date_str)
            if 1900 <= year <= 2100:
                return f"{year}-01-01"
        except ValueError:
            pass

    # Try DD/MM/YYYY or DD-MM-YYYY
    for fmt in ["%d/%m/%Y", "%d-%m-%Y"]:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.date().isoformat()
        except ValueError:
            pass

    logger.warning(f"Could not parse date: {date_str}")
    return None


class SupabaseDB:
    """Supabase Database Client"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client (Singleton)"""
        if cls._instance is None:
            if not settings.supabase_url or not settings.supabase_service_key:
                raise ValueError("Supabase credentials not configured")
            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
        return cls._instance
    
    @classmethod
    def get_anon_client(cls) -> Client:
        """Get anonymous client for public operations"""
        return create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )


class ReportRepository:
    """Repository for Report operations"""
    
    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "reports"
    
    def generate_ticket_id(self) -> str:
        """Generate unique 8-character ticket ID"""
        return uuid.uuid4().hex[:8].upper()
    
    async def create(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new report"""
        ticket_id = self.generate_ticket_id()

        # Sanitize user inputs to prevent XSS
        record = {
            "id": str(uuid.uuid4()),
            "ticket_id": ticket_id,
            "channel": report_data.get("channel", "WEB"),
            "is_anonymous": report_data.get("is_anonymous", True),
            "title": sanitize_input(report_data.get("subject", "")),
            "description": sanitize_input(report_data.get("description", "")),
            "incident_date": parse_date_safe(report_data.get("incident_date")),
            "incident_location": sanitize_input(report_data.get("incident_location") or ""),
            "involved_parties": sanitize_list(report_data.get("parties_involved", [])),
            "reporter_contact": sanitize_input(report_data.get("reporter_contact") or ""),
            "status": "NEW",
            "severity": None,
            "category": report_data.get("category") or None,
            "fraud_score": None,
            "ai_analysis": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table(self.table).insert(record).execute()
        logger.info(f"Created report with ticket_id: {ticket_id}")
        
        # Create audit log
        await self._create_audit_log(
            record["id"],
            "REPORT_CREATED",
            {"ticket_id": ticket_id, "channel": record["channel"]}
        )
        
        return result.data[0] if result.data else record
    
    async def get_by_ticket_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get report by ticket ID"""
        result = self.db.table(self.table)\
            .select("*")\
            .eq("ticket_id", ticket_id.upper())\
            .execute()
        return result.data[0] if result.data else None
    
    async def get_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report by ID"""
        result = self.db.table(self.table)\
            .select("*")\
            .eq("id", report_id)\
            .execute()
        return result.data[0] if result.data else None
    
    async def update_status(
        self, 
        report_id: str, 
        new_status: str,
        updated_by: str = "SYSTEM"
    ) -> Dict[str, Any]:
        """Update report status"""
        result = self.db.table(self.table)\
            .update({
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", report_id)\
            .execute()
        
        await self._create_audit_log(
            report_id,
            "STATUS_CHANGED",
            {"new_status": new_status, "updated_by": updated_by}
        )
        
        return result.data[0] if result.data else None
    
    async def update_analysis(
        self,
        report_id: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update AI analysis results and calculate SLA deadlines"""
        from config import SEVERITY_LEVELS

        update_data = {
            "severity": analysis.get("severity"),
            "category": analysis.get("category"),
            "fraud_score": analysis.get("fraud_score"),
            "ai_analysis": analysis,
            "status": "REVIEWING",
            "updated_at": datetime.utcnow().isoformat()
        }

        # Calculate SLA deadlines based on severity
        severity = analysis.get("severity", "MEDIUM")
        sla_config = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS["MEDIUM"])

        # Get report created_at for SLA calculation
        report = await self.get_by_id(report_id)
        if report:
            created_at = report.get("created_at", datetime.utcnow().isoformat())
            try:
                if isinstance(created_at, str):
                    base_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    base_time = created_at
            except (ValueError, TypeError):
                base_time = datetime.utcnow()

            from datetime import timedelta
            update_data["sla_response_deadline"] = (
                base_time + timedelta(hours=sla_config["sla_initial_hours"])
            ).isoformat()
            update_data["sla_review_deadline"] = (
                base_time + timedelta(hours=sla_config["sla_investigation_hours"])
            ).isoformat()
            update_data["sla_investigation_deadline"] = (
                base_time + timedelta(days=sla_config["sla_resolution_days"])
            ).isoformat()

        result = self.db.table(self.table)\
            .update(update_data)\
            .eq("id", report_id)\
            .execute()

        await self._create_audit_log(
            report_id,
            "AI_ANALYSIS_COMPLETED",
            {
                "severity": analysis.get("severity"),
                "fraud_score": analysis.get("fraud_score")
            }
        )

        return result.data[0] if result.data else None

    async def get_sla_at_risk_count(self) -> int:
        """Count reports where SLA deadline is approaching (within 24h) or breached"""
        now = datetime.utcnow().isoformat()
        upcoming = (datetime.utcnow() + timedelta(hours=24)).isoformat()

        # Reports with SLA deadlines that are breached or within 24h
        # Only count non-closed reports
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
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List reports with filters"""
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
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)
        if search:
            safe_search = sanitize_search_query(search)
            if safe_search:
                query = query.or_(f"title.ilike.%{safe_search}%,description.ilike.%{safe_search}%,ticket_id.ilike.%{safe_search}%")

        is_desc = sort_order.lower() == "desc"
        allowed_sort = {"created_at", "severity", "status", "category"}
        sort_field = sort_by if sort_by in allowed_sort else "created_at"
        query = query.order(sort_field, desc=is_desc)\
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
        assigned_to: Optional[str] = None
    ) -> int:
        """Get total count of reports matching filters"""
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
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)
        if search:
            safe_search = sanitize_search_query(search)
            if safe_search:
                query = query.or_(f"title.ilike.%{safe_search}%,description.ilike.%{safe_search}%,ticket_id.ilike.%{safe_search}%")

        result = query.execute()
        return result.count if result.count is not None else len(result.data or [])
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        all_reports = self.db.table(self.table).select("status, severity, category").execute()
        
        stats = {
            "total": len(all_reports.data) if all_reports.data else 0,
            "by_status": {},
            "by_severity": {},
            "by_category": {}
        }
        
        for report in (all_reports.data or []):
            status = report.get("status") or "UNKNOWN"
            severity = report.get("severity") or "UNASSIGNED"
            category = report.get("category") or "UNASSIGNED"
            
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        return stats
    
    async def _create_audit_log(
        self,
        report_id: str,
        action: str,
        details: Dict[str, Any]
    ):
        """Create audit trail entry"""
        try:
            self.db.table("audit_logs").insert({
                "id": str(uuid.uuid4()),
                "report_id": report_id,
                "action": action,
                "details": details,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")


class MessageRepository:
    """Repository for Message/Communication operations"""
    
    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "messages"
    
    async def create(
        self,
        report_id: str,
        content: str,
        sender_type: str = "REPORTER",
        attachments: List[str] = None,
        ticket_id: str = None
    ) -> Dict[str, Any]:
        """Create new message"""
        # Sanitize message content to prevent XSS
        record = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "ticket_id": ticket_id,
            "content": sanitize_input(content),
            "sender_type": sender_type,  # REPORTER, ADMIN, SYSTEM
            "has_attachments": bool(attachments),
            "is_read": False,
            "created_at": datetime.utcnow().isoformat()
        }

        result = self.db.table(self.table).insert(record).execute()
        return result.data[0] if result.data else record
    
    async def get_by_report(self, report_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a report"""
        result = self.db.table(self.table)\
            .select("*")\
            .eq("report_id", report_id)\
            .order("created_at", desc=False)\
            .execute()
        return result.data or []
    
    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark message as read"""
        result = self.db.table(self.table)\
            .update({"is_read": True})\
            .eq("id", message_id)\
            .execute()
        return result.data[0] if result.data else None


class VectorRepository:
    """Repository for Vector/RAG operations"""
    
    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "knowledge_vectors"
    
    async def store_embedding(
        self,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store document embedding"""
        record = {
            "id": str(uuid.uuid4()),
            "content": content,
            "embedding": embedding,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table(self.table).insert(record).execute()
        return result.data[0] if result.data else record
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search similar documents using vector similarity"""
        # Using Supabase RPC for pgvector similarity search
        result = self.db.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit
            }
        ).execute()
        
        return result.data or []
    
    async def store_case_history(
        self,
        report_id: str,
        summary: str,
        embedding: List[float],
        outcome: str
    ) -> Dict[str, Any]:
        """Store case history for similar case matching"""
        record = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "summary": summary,
            "embedding": embedding,
            "outcome": outcome,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("case_history").insert(record).execute()
        return result.data[0] if result.data else record


class UserRepository:
    """Repository for User operations"""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "users"

    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user"""
        record = {
            "id": str(uuid.uuid4()),
            "email": user_data["email"].lower(),
            "password_hash": user_data["password_hash"],
            "full_name": user_data["full_name"],
            "employee_id": user_data.get("employee_id"),
            "department": user_data.get("department"),
            "phone": user_data.get("phone"),
            "role": user_data.get("role", "INTAKE_OFFICER"),
            "status": "ACTIVE",
            "must_change_password": user_data.get("must_change_password", False),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = self.db.table(self.table).insert(record).execute()
        logger.info(f"Created user: {record['email']}")

        return result.data[0] if result.data else record

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        result = self.db.table(self.table)\
            .select("*")\
            .eq("email", email.lower())\
            .execute()
        return result.data[0] if result.data else None

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        result = self.db.table(self.table)\
            .select("*")\
            .eq("id", user_id)\
            .execute()
        return result.data[0] if result.data else None

    async def update_last_login(self, user_id: str) -> None:
        """Update last login timestamp"""
        self.db.table(self.table)\
            .update({
                "last_login": datetime.utcnow().isoformat(),
                "login_attempts": 0
            })\
            .eq("id", user_id)\
            .execute()

    async def increment_login_attempts(self, user_id: str) -> int:
        """Increment failed login attempts"""
        user = await self.get_by_id(user_id)
        if not user:
            return 0

        attempts = (user.get("login_attempts") or 0) + 1
        update_data = {"login_attempts": attempts}

        # Lock account after 5 failed attempts
        if attempts >= 5:
            lock_until = datetime.utcnow() + timedelta(minutes=30)
            update_data["locked_until"] = lock_until.isoformat()

        self.db.table(self.table)\
            .update(update_data)\
            .eq("id", user_id)\
            .execute()

        return attempts

    async def is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked"""
        user = await self.get_by_id(user_id)
        if not user or not user.get("locked_until"):
            return False

        locked_until = datetime.fromisoformat(user["locked_until"].replace("Z", "+00:00"))
        return datetime.utcnow().replace(tzinfo=locked_until.tzinfo) < locked_until

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """Update user password"""
        result = self.db.table(self.table)\
            .update({
                "password_hash": password_hash,
                "password_changed_at": datetime.utcnow().isoformat(),
                "must_change_password": False,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", user_id)\
            .execute()
        return bool(result.data)

    async def update_status(self, user_id: str, status: str) -> bool:
        """Update user status"""
        result = self.db.table(self.table)\
            .update({
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", user_id)\
            .execute()
        return bool(result.data)

    async def update_role(self, user_id: str, role: str) -> bool:
        """Update user role"""
        result = self.db.table(self.table)\
            .update({
                "role": role,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", user_id)\
            .execute()
        return bool(result.data)

    async def list_all(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all users with filters"""
        query = self.db.table(self.table).select("*")

        if role:
            query = query.eq("role", role)
        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)

        result = query.execute()
        return result.data or []

    async def delete(self, user_id: str) -> bool:
        """Delete user (soft delete by setting status to INACTIVE)"""
        return await self.update_status(user_id, "INACTIVE")


class SessionRepository:
    """Repository for User Session operations"""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "user_sessions"

    async def create(
        self,
        user_id: str,
        token_hash: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create new session"""
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=7)

        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "token_hash": token_hash,
            "device_info": device_info,
            "ip_address": ip_address,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }

        result = self.db.table(self.table).insert(record).execute()
        return result.data[0] if result.data else record

    async def revoke(self, session_id: str) -> bool:
        """Revoke a session"""
        result = self.db.table(self.table)\
            .update({"revoked_at": datetime.utcnow().isoformat()})\
            .eq("id", session_id)\
            .execute()
        return bool(result.data)

    async def revoke_all_for_user(self, user_id: str) -> bool:
        """Revoke all sessions for a user"""
        result = self.db.table(self.table)\
            .update({"revoked_at": datetime.utcnow().isoformat()})\
            .eq("user_id", user_id)\
            .is_("revoked_at", "null")\
            .execute()
        return bool(result.data)


# Export repository instances
report_repo = ReportRepository()
message_repo = MessageRepository()
vector_repo = VectorRepository()
user_repo = UserRepository()
session_repo = SessionRepository()
