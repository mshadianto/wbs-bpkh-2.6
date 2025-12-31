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
- `audit_logs` - Complete audit trail of all actions
- `knowledge_vectors` - RAG document embeddings
- `case_history` - Historical cases for similar case matching

Repository classes in `backend/database.py`: `ReportRepository`, `MessageRepository`, `VectorRepository`.

### API Structure

All endpoints prefixed with `/api/v1/`:
- `/reports` - Admin CRUD operations on reports
- `/tickets` - Public endpoints for anonymous whistleblowers to track their reports
- `/analysis` - Trigger AI analysis on reports
- `/dashboard` - Statistics for admin dashboard
- `/reference` - Static reference data (statuses, severities, categories)
- `/knowledge` - Knowledge base management

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

## Key Patterns

- All agent classes use Groq client with JSON response format
- Background tasks for AI analysis after report submission
- Ticket IDs are 8-character uppercase hex strings for anonymous tracking
- Status transitions are constrained by `STATUS_LIFECYCLE` mapping
- Audit logs created automatically for key actions

## Environment Variables

Required in `.env`:
```
GROQ_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
```

Optional for WhatsApp/Email integrations: `WAHA_API_URL`, `SMTP_*`, etc.
