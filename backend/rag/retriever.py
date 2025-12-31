"""
WBS BPKH AI - RAG Retriever
===========================
Retrieves relevant context from knowledge base.
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from .embeddings import embedding_service, chunking_service
from database import SupabaseDB


class RAGRetriever:
    """
    RAG Retriever - Retrieves relevant context for analysis
    
    Sources:
    - Regulations knowledge base
    - Historical cases
    - Internal policies
    """
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.db = SupabaseDB.get_client()
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        doc_types: Optional[List[str]] = None
    ) -> str:
        """
        Retrieve relevant context for a query
        
        Args:
            query: Search query
            top_k: Number of results
            threshold: Minimum similarity threshold
            doc_types: Filter by document types
            
        Returns:
            Combined context string
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)
            
            # Search using Supabase RPC (pgvector)
            results = await self._vector_search(
                query_embedding,
                top_k,
                threshold,
                doc_types
            )
            
            if not results:
                logger.info("No relevant context found, using built-in knowledge")
                return self._get_default_context()
            
            # Combine results into context string
            context_parts = []
            for result in results:
                source = result.get("metadata", {}).get("source", "Unknown")
                content = result.get("content", "")
                context_parts.append(f"[Sumber: {source}]\n{content}")
            
            return "\n\n---\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            return self._get_default_context()
    
    async def _vector_search(
        self,
        embedding: List[float],
        top_k: int,
        threshold: float,
        doc_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search in Supabase"""
        try:
            # Call Supabase RPC function for similarity search
            params = {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": top_k
            }
            
            if doc_types:
                params["filter_doc_types"] = doc_types
            
            result = self.db.rpc("match_documents", params).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    async def retrieve_similar_cases(
        self,
        report_summary: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve similar historical cases"""
        try:
            # Generate embedding for report summary
            embedding = self.embedding_service.embed_text(report_summary)
            
            # Search case history
            result = self.db.rpc(
                "match_cases",
                {
                    "query_embedding": embedding,
                    "match_count": top_k
                }
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Similar cases retrieval error: {e}")
            return []
    
    def _get_default_context(self) -> str:
        """Return default built-in context"""
        return """
KONTEKS REGULASI WHISTLEBLOWING BPKH:

1. DASAR HUKUM:
   - UU 31/1999 jo UU 20/2001 tentang Pemberantasan Tindak Pidana Korupsi
   - UU 28/1999 tentang Penyelenggaraan Negara yang Bersih dan Bebas KKN
   - PP 43/2018 tentang Tata Cara Pelaksanaan Peran Serta Masyarakat
   - PP 71/2000 tentang Tata Cara Pemberian Penghargaan

2. KATEGORI PELANGGARAN:
   - Korupsi dan Suap
   - Gratifikasi
   - Fraud/Kecurangan
   - Benturan Kepentingan
   - Pelanggaran Pengadaan
   - Penyalahgunaan Wewenang
   - Pelanggaran Data Pribadi
   - Pelanggaran Etika dan Disiplin

3. PERLINDUNGAN PELAPOR (ISO 37002):
   - Kerahasiaan identitas
   - Perlindungan dari pembalasan
   - Hak mendapat informasi perkembangan
   - Komunikasi dua arah yang aman

4. PRINSIP PENANGANAN:
   - Independensi dan objektivitas
   - Kerahasiaan dan keamanan
   - Profesionalisme dan akuntabilitas
   - Proporsionalitas tindakan
"""


class KnowledgeIndexer:
    """Index documents into vector store"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.chunking_service = chunking_service
        self.db = SupabaseDB.get_client()
    
    async def index_document(
        self,
        content: str,
        source: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Index a document into the knowledge base
        
        Returns:
            Number of chunks indexed
        """
        # Chunk the document
        chunks = self.chunking_service.chunk_with_metadata(
            content, source, doc_type
        )
        
        # Generate embeddings
        texts = [c["content"] for c in chunks]
        embeddings = self.embedding_service.embed_batch(texts)
        
        # Store in Supabase
        records = []
        for chunk, embedding in zip(chunks, embeddings):
            record = {
                "content": chunk["content"],
                "embedding": embedding,
                "metadata": {
                    **chunk["metadata"],
                    **(metadata or {})
                }
            }
            records.append(record)
        
        # Batch insert
        try:
            self.db.table("knowledge_vectors").insert(records).execute()
            logger.info(f"Indexed {len(records)} chunks from {source}")
            return len(records)
        except Exception as e:
            logger.error(f"Indexing error: {e}")
            return 0
    
    async def index_regulation(
        self,
        regulation_name: str,
        regulation_text: str,
        articles: List[Dict[str, str]]
    ) -> int:
        """Index a regulation with its articles"""
        total_indexed = 0
        
        # Index full regulation
        total_indexed += await self.index_document(
            content=regulation_text,
            source=regulation_name,
            doc_type="REGULATION",
            metadata={"regulation": regulation_name}
        )
        
        # Index individual articles
        for article in articles:
            total_indexed += await self.index_document(
                content=f"Pasal {article['number']}: {article['content']}",
                source=f"{regulation_name} - Pasal {article['number']}",
                doc_type="ARTICLE",
                metadata={
                    "regulation": regulation_name,
                    "article_number": article["number"]
                }
            )
        
        return total_indexed


# Export instances
rag_retriever = RAGRetriever()
knowledge_indexer = KnowledgeIndexer()
