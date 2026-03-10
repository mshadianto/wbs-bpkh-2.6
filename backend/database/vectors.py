"""
WBS BPKH AI - Vector Repository
================================
Operations for RAG embeddings and case history.
"""

import uuid
from typing import Dict, Any, List
from datetime import datetime

from .client import SupabaseDB


class VectorRepository:
    """Repository for Vector/RAG operations."""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "knowledge_vectors"

    async def store_embedding(
        self, content: str, embedding: List[float], metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Store document embedding."""
        record = {
            "id": str(uuid.uuid4()),
            "content": content,
            "embedding": embedding,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
        }
        result = self.db.table(self.table).insert(record).execute()
        return result.data[0] if result.data else record

    async def similarity_search(
        self, query_embedding: List[float], limit: int = 5, threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search similar documents using vector similarity."""
        result = self.db.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
        }).execute()
        return result.data or []

    async def store_case_history(
        self, report_id: str, summary: str, embedding: List[float], outcome: str,
    ) -> Dict[str, Any]:
        """Store case history for similar case matching."""
        record = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "summary": summary,
            "embedding": embedding,
            "outcome": outcome,
            "created_at": datetime.utcnow().isoformat(),
        }
        result = self.db.table("case_history").insert(record).execute()
        return result.data[0] if result.data else record
