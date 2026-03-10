"""
WBS BPKH AI - Main Application
==============================
FastAPI application for Whistleblowing System.
ISO 37002:2021 Compliant
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn
from loguru import logger

# Suppress noisy HTTP client logs from Groq/httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)

from config import settings
from database import report_repo
from rag import RAGRetriever, KnowledgeLoader
from agents import QuickAnalyzer
from middleware import (
    SecurityHeadersMiddleware,
    RateLimiterMiddleware,
    RequestSizeLimitMiddleware,
)
from routers import (
    auth_router,
    webhooks_router,
    reports_router,
    tickets_router,
    analysis_router,
    dashboard_router,
    investigation_router,
    reference_router,
    knowledge_router,
)


# ============== App Lifecycle ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    logger.info("Starting WBS BPKH AI...")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"LLM Model: {settings.llm_model}")

    if not settings.debug:
        if not settings.jwt_secret or len(settings.jwt_secret) < 32:
            logger.error("JWT_SECRET must be set with at least 32 characters in production!")
            raise ValueError("JWT_SECRET not configured properly")
        if not settings.secret_key or len(settings.secret_key) < 32:
            logger.error("SECRET_KEY must be set with at least 32 characters in production!")
            raise ValueError("SECRET_KEY not configured properly")
        logger.info("Security secrets validated")

    app.state.rag_retriever = RAGRetriever()
    app.state.knowledge_loader = KnowledgeLoader()
    app.state.quick_analyzer = QuickAnalyzer()

    logger.info("Application started successfully")
    yield
    logger.info("Shutting down WBS BPKH AI...")


# ============== FastAPI App ==============

docs_url = "/docs" if settings.debug else None
redoc_url = "/redoc" if settings.debug else None
openapi_url = "/openapi.json" if settings.debug else None

app = FastAPI(
    title="WBS BPKH AI",
    description=(
        "Whistleblowing System BPKH - RAG Agentic AI\n\n"
        "Sistem Pelaporan Pelanggaran berbasis AI untuk "
        "Badan Pengelola Keuangan Haji.\n\n"
        "Compliant with ISO 37002:2021"
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)


# ============== Middleware (order matters: last added = first executed) ==============

# CORS
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

# Security headers (CSP, HSTS, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware, debug=settings.debug)

# Rate limiting (in-memory, per-IP)
app.add_middleware(RateLimiterMiddleware)

# Request body size limit (5MB)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=5 * 1024 * 1024)


# ============== Routers ==============

app.include_router(auth_router)
app.include_router(webhooks_router)
app.include_router(reports_router)
app.include_router(tickets_router)
app.include_router(analysis_router)
app.include_router(dashboard_router)
app.include_router(investigation_router)
app.include_router(reference_router)
app.include_router(knowledge_router)


# ============== Health & Root ==============

@app.get("/", tags=["Frontend"], include_in_schema=False)
async def root():
    """Serve landing page at root."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check with component verification."""
    db_status = "error"
    try:
        report_repo.db.table("reports").select("id").limit(1).execute()
        db_status = "ok"
    except Exception as e:
        logger.warning(f"Health check - DB error: {e}")

    ai_status = "ok" if settings.groq_api_key else "not_configured"
    overall = "healthy" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "components": {
            "api": "ok",
            "database": db_status,
            "ai_engine": ai_status,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============== Static Files & Frontend ==============

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(FRONTEND_PATH):
    app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")


@app.get("/portal", tags=["Frontend"])
async def serve_portal():
    """Serve public reporting portal."""
    file_path = os.path.join(FRONTEND_PATH, "portal_pelaporan.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Portal not found")


@app.get("/dashboard", tags=["Frontend"])
async def serve_dashboard():
    """Serve admin dashboard."""
    file_path = os.path.join(FRONTEND_PATH, "wbs_dashboard.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/login", tags=["Frontend"])
async def serve_login():
    """Serve login page."""
    file_path = os.path.join(FRONTEND_PATH, "login.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Login page not found")


@app.get("/home", tags=["Frontend"])
async def serve_home():
    """Serve landing page."""
    file_path = os.path.join(FRONTEND_PATH, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Home not found")


# ============== Main ==============

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
