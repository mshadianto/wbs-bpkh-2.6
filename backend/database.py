"""
WBS BPKH AI - Database Module
============================
Supabase database client and operations.
"""

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import json
from loguru import logger

from config import settings


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
        
        record = {
            "id": str(uuid.uuid4()),
            "ticket_id": ticket_id,
            "channel": report_data.get("channel", "WEB"),
            "reporter_contact": report_data.get("reporter_contact"),
            "is_anonymous": report_data.get("is_anonymous", True),
            "subject": report_data.get("subject", ""),
            "description": report_data.get("description", ""),
            "incident_date": report_data.get("incident_date"),
            "incident_location": report_data.get("incident_location"),
            "parties_involved": report_data.get("parties_involved", []),
            "status": "NEW",
            "severity": None,
            "category": None,
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
        """Update AI analysis results"""
        result = self.db.table(self.table)\
            .update({
                "severity": analysis.get("severity"),
                "category": analysis.get("category"),
                "fraud_score": analysis.get("fraud_score"),
                "ai_analysis": analysis,
                "status": "REVIEWING",
                "updated_at": datetime.utcnow().isoformat()
            })\
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
    
    async def list_all(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List reports with filters"""
        query = self.db.table(self.table).select("*")
        
        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)
        
        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)
        
        result = query.execute()
        return result.data or []
    
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
            status = report.get("status", "UNKNOWN")
            severity = report.get("severity", "UNASSIGNED")
            category = report.get("category", "UNASSIGNED")
            
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
        attachments: List[str] = None
    ) -> Dict[str, Any]:
        """Create new message"""
        record = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "content": content,
            "sender_type": sender_type,  # REPORTER, ADMIN, SYSTEM
            "attachments": attachments or [],
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


# Export repository instances
report_repo = ReportRepository()
message_repo = MessageRepository()
vector_repo = VectorRepository()
