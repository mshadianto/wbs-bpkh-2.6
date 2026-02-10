# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WBS BPKH AI is a Whistleblowing System for Badan Pengelola Keuangan Haji (Indonesian Hajj Financial Management Agency). AI-powered platform for anonymous violation reporting, compliant with ISO 37002:2021. Reports flow through: `BARU → SEDANG DITINJAU → BUTUH INFO (optional) → DALAM INVESTIGASI → SELESAI`.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **LLM**: Groq API (llama-3.3-70b-versatile)
- **Database**: Supabase (PostgreSQL + pgvector for RAG)
- **Embeddings**: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384-dim vectors)
- **Frontend**: Static HTML5 with TailwindCSS, Chart.js — no JS framework
- **Data Models**: Pydantic v2
- **Logging**: Loguru

## Common Commands

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run backend server (from backend/ directory)
cd backend
uvicorn main:app --reload --port 8000

# Load knowledge base for RAG
python scripts/seed_knowledge.py
python scripts/seed_knowledge.py --reset  # Reset and reload all documents

# Run tests (test directory not yet created)
pytest backend/tests/
pytest -v  # verbose
pytest backend/tests/test_specific.py  # single test file

# Code formatting
black backend/
isort backend/
flake8 backend/

# Docker
docker build -t wbs-bpkh .
docker run -p 8000:8000 --env-file .env wbs-bpkh
```

## Architecture

### Entry Point & Routing

`backend/main.py` is the FastAPI app and contains most API endpoint handlers directly (reports, tickets, analysis, dashboard, reference). Only auth and webhooks are separated into routers:
- `backend/routers/auth.py` — login, register, /me
- `backend/routers/webhooks.py` — WhatsApp (WAHA) and email incoming webhooks

FastAPI also serves the frontend as static files with route aliases: `/portal`, `/dashboard`, `/login`, `/home`.

### Multi-Agent AI Analysis Pipeline

Orchestrated multi-agent architecture in `backend/agents/orchestrator.py`:

1. **IntakeAgent** — Parses 4W+1H (What, Who, When, Where, How) from reports
2. **AnalysisAgent** — Calculates fraud indicators using fraud triangle methodology
3. **ComplianceAgent** — Checks violations against regulations using RAG context
4. **SeverityAgent** — Assesses risk level (CRITICAL/HIGH/MEDIUM/LOW) with SLA mapping
5. **RecommendationAgent** — Generates action items based on all prior analysis
6. **SummaryAgent** — Creates executive summary

`OrchestratorAgent` runs the pipeline sequentially, passing results between agents. `QuickAnalyzer` provides single-prompt analysis for simpler cases. AI analysis is triggered as a FastAPI `BackgroundTask` after report submission so it doesn't block the response.

### RAG System

Located in `backend/rag/`:
- `embeddings.py` — Singleton sentence-transformers model for local embedding generation
- `retriever.py` — `RAGRetriever` fetches context via Supabase pgvector RPC functions (`match_documents`, `match_cases`); `KnowledgeIndexer` handles document indexing
- `knowledge_loader.py` — Loads regulations from `knowledge_base/` directory

### Database Schema

Supabase tables (schema in `scripts/setup_supabase.sql`, auth migration in `database/002_users_auth.sql`):
- `reports` — Whistleblowing reports with ticket IDs, status, AI analysis results
- `messages` — Two-way communication between reporters and admins
- `users` — Admin users with roles and authentication
- `user_sessions` — JWT session management
- `report_assignments` — Investigation assignments
- `audit_logs` — Complete audit trail of all actions
- `knowledge_vectors` — RAG document embeddings
- `case_history` — Historical cases for similar case matching

Repository classes in `backend/database.py`: `ReportRepository`, `MessageRepository`, `VectorRepository`, `UserRepository`, `SessionRepository`.

### Authentication & Authorization

JWT-based auth in `backend/auth.py`:
- Role hierarchy: `REPORTER(0) < INTAKE_OFFICER(1) < INVESTIGATOR(2) < MANAGER(3) < ADMIN(4)`
- Use `require_auth` for authenticated endpoints
- Use `require_role(UserRole.ADMIN)` for exact role
- Use `require_min_role(UserRole.INTAKE_OFFICER)` for minimum role level
- Account lockout after 5 failed login attempts (30 min)
- Password hashing: bcrypt via passlib
- Password requirements: 8+ chars, uppercase, lowercase, digit, special char

### API Structure

All endpoints prefixed with `/api/v1/`:
- `/auth/login`, `/auth/register`, `/auth/me` — Authentication (in `backend/routers/auth.py`)
- `/reports` — Admin CRUD operations on reports (requires INTAKE_OFFICER+)
- `/tickets` — Public endpoints for anonymous whistleblowers to track reports
- `/analysis` — Trigger AI analysis on reports
- `/dashboard` — Statistics for admin dashboard
- `/reference` — Static reference data (statuses, severities, categories)
- `/knowledge` — Knowledge base management (ADMIN only)
- `/webhooks/whatsapp`, `/webhooks/email` — Incoming channel webhooks (in `backend/routers/webhooks.py`)
- `/health` — Health check endpoint

### Multi-Channel Integration

Services in `backend/services/`:
- `whatsapp_service.py` — WAHA API integration for WhatsApp messaging
- `email_service.py` — SMTP email sending with HTML templates
- `notification_service.py` — Unified notification dispatch across channels

WhatsApp commands: `LAPOR: <description>`, `STATUS <ticket_id>`, `<ticket_id> <message>`

### Configuration

`backend/config.py` contains Pydantic Settings and all business logic constants:
- `VIOLATION_CATEGORIES` — 9 violation types with legal bases
- `SEVERITY_LEVELS` — SLA definitions per severity
- `REPORT_STATUS` and `STATUS_LIFECYCLE` — State machine for report workflow
- `ESCALATION_MATRIX` — 4-level escalation rules
- `FRAUD_SCORE_LEVELS` — Interpretation thresholds (0-0.30 Low, 0.31-0.70 Medium, 0.71-1.0 High)

### Frontend

Static HTML files in `frontend/` — role-specific dashboards exist for INVESTIGATOR, MANAGER, and INTAKE_OFFICER with tailored views and AI analysis pages:
- `portal_pelaporan.html` — Public anonymous reporting portal
- `wbs_dashboard.html` — Admin dashboard (large file, ~374KB, contains all role views)
- `login.html` — Admin login page
- `index.html` — Landing page

## Key Patterns

- All agent classes use Groq client with JSON response format (`response_format={"type": "json_object"}`)
- Background tasks for AI analysis after report submission (`BackgroundTasks.add_task`)
- Ticket IDs are 8-character uppercase hex strings for anonymous tracking
- Status transitions are constrained by `STATUS_LIFECYCLE` mapping
- Audit logs created automatically for key actions via `_create_audit_log`
- XSS prevention via `sanitize_input()` in `database.py` for all user inputs
- Security headers middleware adds X-Frame-Options, X-XSS-Protection, etc.
- API docs disabled in production (`docs_url = None` when `debug=False`)
- Pydantic models for all API I/O defined in `backend/models/__init__.py`

## Environment Variables

Required in `.env`:
```
GROQ_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
JWT_SECRET=          # min 32 chars for production
SECRET_KEY=          # min 32 chars for production
```

Optional for WhatsApp/Email integrations:
```
WAHA_API_URL=
WAHA_API_KEY=
WAHA_SESSION=default
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
WBS_EMAIL=wbs@bpkh.go.id
```

## Database Setup

Run `scripts/setup_supabase.sql` in Supabase SQL Editor to create tables:
- Enable pgvector extension first: `create extension if not exists vector;`
- Run `database/002_users_auth.sql` for user/auth tables
- RPC functions: `match_documents`, `match_cases` for vector similarity search
