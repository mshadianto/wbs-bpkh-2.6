# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WBS BPKH AI is a Whistleblowing System for Badan Pengelola Keuangan Haji (Indonesian Hajj Financial Management Agency). It's an AI-powered platform for anonymous violation reporting, compliant with ISO 37002:2021.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **LLM**: Groq API (llama-3.3-70b-versatile)
- **Database**: Supabase (PostgreSQL + pgvector for RAG)
- **Embeddings**: sentence-transformers (local)
- **Frontend**: Static HTML5 with TailwindCSS
- **Data Models**: Pydantic v2

## Common Commands

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run backend server
cd backend
uvicorn main:app --reload --port 8000

# Load knowledge base for RAG
python scripts/seed_knowledge.py

# Run tests
pytest
pytest -v  # verbose
pytest backend/tests/test_specific.py  # single test file

# Code formatting
black backend/
isort backend/
flake8 backend/
```

## Architecture

### Multi-Agent AI Analysis Pipeline

The system uses an orchestrated multi-agent architecture for report analysis (`backend/agents/orchestrator.py`):

1. **IntakeAgent** - Parses 4W+1H (What, Who, When, Where, How) from reports
2. **AnalysisAgent** - Calculates fraud indicators using fraud triangle methodology
3. **ComplianceAgent** - Checks violations against regulations using RAG context
4. **SeverityAgent** - Assesses risk level (CRITICAL/HIGH/MEDIUM/LOW) with SLA mapping
5. **RecommendationAgent** - Generates action items based on all prior analysis
6. **SummaryAgent** - Creates executive summary

The `OrchestratorAgent` coordinates this pipeline sequentially, passing results between agents. A `QuickAnalyzer` class provides single-prompt analysis for simpler cases.

### RAG System

Located in `backend/rag/`:
- `embeddings.py` - sentence-transformers for local embedding generation
- `retriever.py` - RAGRetriever fetches context from knowledge base; KnowledgeIndexer handles document indexing
- `knowledge_loader.py` - Loads regulations from `knowledge_base/` directory

Vector similarity search uses Supabase's pgvector via RPC functions (`match_documents`, `match_cases`).

### Database Schema

Uses Supabase with these main tables:
- `reports` - Whistleblowing reports with ticket IDs, status, AI analysis results
- `messages` - Two-way communication between reporters and admins
- `users` - Admin users with roles and authentication
- `user_sessions` - JWT session management
- `audit_logs` - Complete audit trail of all actions
- `knowledge_vectors` - RAG document embeddings
- `case_history` - Historical cases for similar case matching

Repository classes in `backend/database.py`: `ReportRepository`, `MessageRepository`, `VectorRepository`, `UserRepository`, `SessionRepository`.

### Authentication & Authorization

JWT-based authentication in `backend/auth.py`:
- Role hierarchy: `REPORTER < INTAKE_OFFICER < INVESTIGATOR < MANAGER < ADMIN`
- Use `require_auth` for authenticated endpoints
- Use `require_role(UserRole.ADMIN)` for specific role
- Use `require_min_role(UserRole.INTAKE_OFFICER)` for minimum role level
- Account lockout after 5 failed login attempts (30 min)
- Password requirements: 8+ chars, uppercase, lowercase, digit, special char

### API Structure

All endpoints prefixed with `/api/v1/`:
- `/auth/login`, `/auth/register`, `/auth/me` - Authentication (in `backend/routers/auth.py`)
- `/reports` - Admin CRUD operations on reports (requires INTAKE_OFFICER+)
- `/tickets` - Public endpoints for anonymous whistleblowers to track their reports
- `/analysis` - Trigger AI analysis on reports
- `/dashboard` - Statistics for admin dashboard
- `/reference` - Static reference data (statuses, severities, categories)
- `/knowledge` - Knowledge base management (ADMIN only)
- `/webhooks/whatsapp`, `/webhooks/email` - Incoming channel webhooks (in `backend/routers/webhooks.py`)

### Multi-Channel Integration

Services in `backend/services/`:
- `whatsapp_service.py` - WAHA API integration for WhatsApp messaging
- `email_service.py` - SMTP email sending with HTML templates
- `notification_service.py` - Unified notification dispatch across channels

WhatsApp commands: `LAPOR: <description>`, `STATUS <ticket_id>`, `<ticket_id> <message>`

### Configuration

`backend/config.py` contains all business logic constants:
- `VIOLATION_CATEGORIES` - 9 violation types with legal bases
- `SEVERITY_LEVELS` - SLA definitions per severity
- `REPORT_STATUS` and `STATUS_LIFECYCLE` - State machine for report workflow
- `ESCALATION_MATRIX` - 4-level escalation rules
- `FRAUD_SCORE_LEVELS` - Interpretation thresholds (0-0.30 Low, 0.31-0.70 Medium, 0.71-1.0 High)

### Frontend

Static HTML files in `frontend/`:
- `portal_pelaporan.html` - Public anonymous reporting portal
- `wbs_dashboard.html` - Admin dashboard
- `login.html` - Admin login page
- `index.html` - Landing page

Frontend routes served by FastAPI: `/portal`, `/dashboard`, `/login`, `/home`

## Key Patterns

- All agent classes use Groq client with JSON response format (`response_format={"type": "json_object"}`)
- Background tasks for AI analysis after report submission (`BackgroundTasks.add_task`)
- Ticket IDs are 8-character uppercase hex strings for anonymous tracking
- Status transitions are constrained by `STATUS_LIFECYCLE` mapping
- Audit logs created automatically for key actions via `_create_audit_log`
- XSS prevention via `sanitize_input()` in database.py for all user inputs
- Security headers middleware adds X-Frame-Options, X-XSS-Protection, etc.
- API docs disabled in production (`docs_url = None` when `debug=False`)

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
