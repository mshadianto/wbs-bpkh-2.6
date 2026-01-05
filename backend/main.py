"""
WBS BPKH AI - Main Application
==============================
FastAPI application for Whistleblowing System.
ISO 37002:2021 Compliant
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
import uvicorn
from loguru import logger

# Suppress noisy HTTP client logs from Groq/httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)

from config import settings, REPORT_STATUS, SEVERITY_LEVELS, VIOLATION_CATEGORIES
from database import report_repo, message_repo
from agents import OrchestratorAgent, QuickAnalyzer
from rag import RAGRetriever, KnowledgeLoader
from models import (
    ReportCreate, ReportResponse, ReportDetail, ReportListResponse,
    MessageCreate, MessageResponse,
    AnalysisRequest, FullAnalysisResponse,
    DashboardStats, StatusUpdate,
    TicketLookup, TicketStatusResponse
)
from routers import auth_router
from auth import require_auth, require_role, require_min_role, UserRole, TokenData


# ============== App Lifecycle ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info("🚀 Starting WBS BPKH AI...")
    logger.info(f"📋 Version: {settings.app_version}")
    logger.info(f"🤖 LLM Model: {settings.llm_model}")

    # Security: Validate required secrets are configured
    if not settings.debug:
        if not settings.jwt_secret or len(settings.jwt_secret) < 32:
            logger.error("❌ JWT_SECRET must be set with at least 32 characters in production!")
            raise ValueError("JWT_SECRET not configured properly")
        if not settings.secret_key or len(settings.secret_key) < 32:
            logger.error("❌ SECRET_KEY must be set with at least 32 characters in production!")
            raise ValueError("SECRET_KEY not configured properly")
        logger.info("🔐 Security secrets validated")

    # Initialize RAG retriever
    app.state.rag_retriever = RAGRetriever()
    app.state.knowledge_loader = KnowledgeLoader()
    app.state.quick_analyzer = QuickAnalyzer()

    logger.info("✅ Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down WBS BPKH AI...")


# ============== FastAPI App ==============

# Disable API docs in production for security
docs_url = "/docs" if settings.debug else None
redoc_url = "/redoc" if settings.debug else None
openapi_url = "/openapi.json" if settings.debug else None

app = FastAPI(
    title="WBS BPKH AI",
    description="""
    ## Whistleblowing System BPKH - RAG Agentic AI

    Sistem Pelaporan Pelanggaran berbasis AI untuk Badan Pengelola Keuangan Haji.

    **Fitur Utama:**
    - 🔐 Pelaporan anonim dan terenkripsi
    - 🤖 Analisis otomatis dengan Multi-Agent AI
    - 📊 Dashboard monitoring real-time
    - 📝 Komunikasi dua arah yang aman
    - 📈 Audit trail lengkap

    **Compliant with ISO 37002:2021**
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url
)

# CORS Middleware - Configured for security
ALLOWED_ORIGINS = [
    "https://wbs.bpkh.go.id",
    "https://wbs-bpkh.up.railway.app",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Include Routers
app.include_router(auth_router)


# ============== Health Check ==============

@app.get("/", tags=["Frontend"], include_in_schema=False)
async def root():
    """Serve landing page at root"""
    file_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    # Fallback to health check if landing page not found
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "database": "ok",  # Add actual check
            "ai_engine": "ok"  # Add actual check
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ============== Report Endpoints ==============

@app.post("/api/v1/reports", response_model=ReportResponse, tags=["Reports"])
async def create_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks
):
    """
    Submit new whistleblowing report
    
    Returns ticket ID for tracking.
    AI analysis runs in background.
    """
    try:
        # Create report in database
        report_data = report.model_dump()
        created_report = await report_repo.create(report_data)
        
        # Schedule AI analysis in background
        background_tasks.add_task(
            run_ai_analysis,
            created_report["id"],
            report.description,
            app.state.rag_retriever
        )
        
        logger.info(f"Report created: {created_report['ticket_id']}")
        
        return ReportResponse(
            id=created_report["id"],
            ticket_id=created_report["ticket_id"],
            channel=created_report["channel"],
            status=created_report["status"],
            subject=created_report.get("title", ""),
            description=created_report["description"][:200] + "...",
            is_anonymous=created_report["is_anonymous"],
            created_at=created_report["created_at"],
            updated_at=created_report["updated_at"]
        )
        
    except Exception as e:
        logger.error(f"Failed to create report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reports", response_model=ReportListResponse, tags=["Reports"])
async def list_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))
):
    """List all reports (Intake Officer and above)"""
    try:
        offset = (page - 1) * per_page
        reports = await report_repo.list_all(
            status=status,
            severity=severity,
            limit=per_page,
            offset=offset
        )
        
        return ReportListResponse(
            total=len(reports),  # Should be total count from DB
            reports=[ReportResponse(**r) for r in reports],
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reports/{report_id}", response_model=ReportDetail, tags=["Reports"])
async def get_report(
    report_id: str,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))
):
    """Get report details (Intake Officer and above)"""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get message count
        messages = await message_repo.get_by_report(report_id)
        
        return ReportDetail(
            **report,
            messages_count=len(messages)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/v1/reports/{report_id}/status", tags=["Reports"])
async def update_report_status(
    report_id: str,
    update: StatusUpdate,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))
):
    """Update report status (Intake Officer and above)"""
    try:
        report = await report_repo.update_status(
            report_id,
            update.new_status.value,
            updated_by=current_user.email
        )
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {"message": "Status updated", "new_status": update.new_status.value}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Ticket Endpoints (Public) ==============

@app.post("/api/v1/tickets/lookup", response_model=TicketStatusResponse, tags=["Tickets"])
async def lookup_ticket(lookup: TicketLookup):
    """
    Public endpoint for whistleblowers to check their report status
    """
    try:
        report = await report_repo.get_by_ticket_id(lookup.ticket_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Map status to user-friendly description
        status_descriptions = {
            "NEW": "Laporan Anda telah diterima dan sedang menunggu ditinjau",
            "REVIEWING": "Laporan Anda sedang dalam proses telaah oleh tim kami",
            "NEED_INFO": "Tim kami memerlukan informasi tambahan dari Anda",
            "INVESTIGATING": "Laporan Anda sedang dalam proses investigasi",
            "HOLD": "Penanganan laporan sedang ditangguhkan sementara",
            "ESCALATED": "Laporan Anda telah dieskalasi ke pihak berwenang",
            "CLOSED_PROVEN": "Investigasi selesai - Laporan terbukti",
            "CLOSED_NOT_PROVEN": "Investigasi selesai - Tidak cukup bukti",
            "CLOSED_INVALID": "Laporan ditutup - Tidak dalam lingkup WBS"
        }
        
        return TicketStatusResponse(
            ticket_id=report["ticket_id"],
            status=report["status"],
            status_description=status_descriptions.get(
                report["status"], 
                "Status sedang diproses"
            ),
            last_updated=report["updated_at"],
            can_add_info=report["status"] in ["NEW", "REVIEWING", "NEED_INFO"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ticket lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tickets/{ticket_id}/messages", tags=["Tickets"])
async def add_message_by_ticket(
    ticket_id: str,
    message: MessageCreate
):
    """
    Add message/additional info to a report using ticket ID
    (Public endpoint for whistleblowers)
    """
    try:
        report = await report_repo.get_by_ticket_id(ticket_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        if report["status"] not in ["NEW", "REVIEWING", "NEED_INFO"]:
            raise HTTPException(
                status_code=400, 
                detail="Tidak dapat menambah informasi pada status ini"
            )
        
        # Create message
        msg = await message_repo.create(
            report_id=report["id"],
            content=message.content,
            sender_type="REPORTER",
            attachments=message.attachments,
            ticket_id=ticket_id
        )
        
        return {"message": "Informasi berhasil ditambahkan", "message_id": msg["id"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tickets/{ticket_id}/messages", tags=["Tickets"])
async def get_messages_by_ticket(ticket_id: str):
    """Get messages for a ticket (Public - filtered for reporter)"""
    try:
        report = await report_repo.get_by_ticket_id(ticket_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        messages = await message_repo.get_by_report(report["id"])
        
        # Filter out internal admin notes if needed
        public_messages = [
            {
                "id": m["id"],
                "content": m["content"],
                "sender": "Anda" if m["sender_type"] == "REPORTER" else "Tim WBS",
                "created_at": m["created_at"]
            }
            for m in messages
            if m["sender_type"] in ["REPORTER", "ADMIN"]
        ]
        
        return {"messages": public_messages}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Analysis Endpoints ==============

@app.post("/api/v1/analysis/run", response_model=FullAnalysisResponse, tags=["Analysis"])
async def run_analysis(
    request: AnalysisRequest,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))
):
    """
    Manually trigger AI analysis for a report (Intake Officer and above)
    """
    try:
        report = await report_repo.get_by_id(request.report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get RAG context
        rag_context = await app.state.rag_retriever.retrieve_context(
            report["description"]
        )
        
        # Get similar cases
        similar_cases = await app.state.rag_retriever.retrieve_similar_cases(
            report["description"]
        )
        
        if request.use_full_analysis:
            # Full multi-agent analysis
            orchestrator = OrchestratorAgent(rag_context=rag_context)
            analysis = await orchestrator.analyze_report(
                report_content=report["description"],
                similar_cases=similar_cases
            )
        else:
            # Quick single-prompt analysis
            analysis = await app.state.quick_analyzer.quick_analyze(
                report["description"]
            )
        
        # Update report with analysis results
        await report_repo.update_analysis(request.report_id, analysis)
        
        return FullAnalysisResponse(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analysis/{report_id}", tags=["Analysis"])
async def get_analysis(
    report_id: str,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))
):
    """Get analysis results for a report (Intake Officer and above)"""
    try:
        report = await report_repo.get_by_id(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if not report.get("ai_analysis"):
            raise HTTPException(status_code=404, detail="Analysis not available")
        
        return report["ai_analysis"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Dashboard Endpoints ==============

@app.get("/api/v1/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard_stats(
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))
):
    """Get dashboard statistics (Intake Officer and above)"""
    try:
        stats = await report_repo.get_statistics()
        
        return DashboardStats(
            total_reports=stats["total"],
            by_status=stats["by_status"],
            by_severity=stats["by_severity"],
            by_category=stats["by_category"],
            pending_review=stats["by_status"].get("NEW", 0) + 
                          stats["by_status"].get("REVIEWING", 0),
            sla_at_risk=0  # Calculate based on SLA deadlines
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Reference Data Endpoints ==============

@app.get("/api/v1/reference/statuses", tags=["Reference"])
async def get_statuses():
    """Get all possible report statuses"""
    return REPORT_STATUS


@app.get("/api/v1/reference/severities", tags=["Reference"])
async def get_severities():
    """Get severity levels with SLA"""
    return SEVERITY_LEVELS


@app.get("/api/v1/reference/categories", tags=["Reference"])
async def get_categories():
    """Get violation categories"""
    return VIOLATION_CATEGORIES


# ============== Knowledge Base Endpoints ==============

@app.post("/api/v1/knowledge/load", tags=["Knowledge"])
async def load_knowledge_base(
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """Load all regulations into knowledge base (Admin only)"""
    try:
        results = await app.state.knowledge_loader.load_all()
        return {
            "message": "Knowledge base loaded",
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Background Tasks ==============

async def run_ai_analysis(
    report_id: str,
    description: str,
    rag_retriever: RAGRetriever
):
    """Background task to run AI analysis"""
    try:
        logger.info(f"Starting background analysis for report {report_id}")
        
        # Get RAG context
        rag_context = await rag_retriever.retrieve_context(description)
        
        # Get similar cases
        similar_cases = await rag_retriever.retrieve_similar_cases(description)
        
        # Run analysis
        orchestrator = OrchestratorAgent(rag_context=rag_context)
        analysis = await orchestrator.analyze_report(
            report_content=description,
            similar_cases=similar_cases
        )
        
        # Update report
        await report_repo.update_analysis(report_id, analysis)
        
        logger.info(f"Analysis completed for report {report_id}")
        
    except Exception as e:
        logger.error(f"Background analysis failed for {report_id}: {e}")


# ============== Static Files & Frontend ==============

# Get frontend path (relative to backend folder)
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend")

# Serve frontend static files
if os.path.exists(FRONTEND_PATH):
    app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

@app.get("/portal", tags=["Frontend"])
async def serve_portal():
    """Serve public reporting portal"""
    file_path = os.path.join(FRONTEND_PATH, "portal_pelaporan.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Portal not found")

@app.get("/dashboard", tags=["Frontend"])
async def serve_dashboard():
    """Serve admin dashboard"""
    file_path = os.path.join(FRONTEND_PATH, "wbs_dashboard.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get("/login", tags=["Frontend"])
async def serve_login():
    """Serve login page"""
    file_path = os.path.join(FRONTEND_PATH, "login.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Login page not found")

@app.get("/home", tags=["Frontend"])
async def serve_home():
    """Serve landing page"""
    file_path = os.path.join(FRONTEND_PATH, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Home not found")


# ============== Main ==============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
