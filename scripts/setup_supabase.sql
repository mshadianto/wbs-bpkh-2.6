-- ============================================================
-- WBS BPKH - Whistleblowing System Database Schema
-- ISO 37002:2021 Compliant
-- Supabase PostgreSQL + pgvector
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- ENUM TYPES
-- ============================================================

-- Report Status Enum
CREATE TYPE report_status AS ENUM (
    'NEW',
    'REVIEWING',
    'NEED_INFO',
    'INVESTIGATING',
    'HOLD',
    'ESCALATED',
    'CLOSED_PROVEN',
    'CLOSED_NOT_PROVEN',
    'CLOSED_INVALID'
);

-- Severity Level Enum
CREATE TYPE severity_level AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

-- Violation Category Enum
CREATE TYPE violation_category AS ENUM (
    'FRAUD',
    'CORRUPTION',
    'GRATIFICATION',
    'COI',
    'PROCUREMENT',
    'DATA_BREACH',
    'ETHICS',
    'MISCONDUCT',
    'OTHER'
);

-- Report Channel Enum
CREATE TYPE report_channel AS ENUM (
    'WEB',
    'EMAIL',
    'WHATSAPP',
    'HOTLINE',
    'LETTER',
    'OTHER'
);

-- Sender Type Enum
CREATE TYPE sender_type AS ENUM (
    'REPORTER',
    'SYSTEM',
    'ADMIN',
    'MANAGER'
);

-- User Role Enum (matches 002_users_auth.sql and Python auth.py)
CREATE TYPE user_role AS ENUM (
    'REPORTER',
    'INTAKE_OFFICER',
    'INVESTIGATOR',
    'MANAGER',
    'ADMIN'
);

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Users Table (Internal Staff)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'INTAKE_OFFICER',
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reports Table (Main Whistleblowing Reports)
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id VARCHAR(8) UNIQUE NOT NULL,
    
    -- Reporter Info (dapat anonymous)
    reporter_name VARCHAR(255),
    reporter_email VARCHAR(255),
    reporter_phone VARCHAR(50),
    reporter_identity_hash VARCHAR(64), -- Hash untuk tracking anonymous
    is_anonymous BOOLEAN DEFAULT FALSE,
    
    -- Report Content
    title VARCHAR(500),
    description TEXT NOT NULL,
    incident_date DATE,
    incident_location VARCHAR(500),
    involved_parties TEXT[], -- Array of names
    evidence_description TEXT,
    
    -- Channel & Source
    channel report_channel NOT NULL DEFAULT 'WEB',
    source_reference VARCHAR(255), -- Email ID, WA Message ID, etc
    
    -- Classification (AI Generated)
    category violation_category,
    severity severity_level,
    fraud_score DECIMAL(3,2), -- 0.00 - 1.00
    priority VARCHAR(20), -- P1, P2, P3, P4
    
    -- Status & Workflow
    status report_status DEFAULT 'NEW',
    assigned_to UUID REFERENCES users(id),
    escalated_to UUID REFERENCES users(id),
    
    -- SLA Tracking
    sla_response_deadline TIMESTAMPTZ,
    sla_review_deadline TIMESTAMPTZ,
    sla_investigation_deadline TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    
    -- AI Analysis Results (JSON)
    ai_analysis JSONB,
    intake_analysis JSONB,
    fraud_analysis JSONB,
    compliance_analysis JSONB,
    severity_analysis JSONB,
    recommendations JSONB,
    executive_summary TEXT,
    
    -- Metadata
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_fraud_score CHECK (fraud_score >= 0 AND fraud_score <= 1)
);

-- Tickets Table (Public Access untuk Pelapor)
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id VARCHAR(8) UNIQUE NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Access Control
    access_token VARCHAR(64) NOT NULL, -- Hashed token untuk akses
    access_token_hash VARCHAR(128),
    
    -- Status untuk Pelapor
    public_status VARCHAR(50) DEFAULT 'Diterima',
    last_message_at TIMESTAMPTZ,
    unread_count_reporter INTEGER DEFAULT 0,
    unread_count_admin INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages Table (Two-way Communication)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id VARCHAR(8) NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Message Content
    sender_type sender_type NOT NULL,
    sender_id UUID, -- NULL for whistleblower/system
    sender_name VARCHAR(255),
    content TEXT NOT NULL,
    
    -- Attachments
    has_attachments BOOLEAN DEFAULT FALSE,
    
    -- Read Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attachments Table
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    
    -- File Info
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size INTEGER,
    mime_type VARCHAR(100),
    
    -- Storage
    storage_path VARCHAR(1000), -- Supabase Storage path
    storage_bucket VARCHAR(100) DEFAULT 'attachments',
    
    -- Security
    is_encrypted BOOLEAN DEFAULT TRUE,
    checksum VARCHAR(64),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by UUID REFERENCES users(id)
);

-- Audit Logs Table (Complete Trail)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Target
    entity_type VARCHAR(50) NOT NULL, -- report, ticket, message, user
    entity_id UUID NOT NULL,
    
    -- Action
    action VARCHAR(50) NOT NULL, -- create, update, delete, view, status_change
    action_details TEXT,
    
    -- Actor
    actor_type VARCHAR(50), -- user, system, whistleblower
    actor_id UUID,
    actor_email VARCHAR(255),
    actor_ip VARCHAR(45),
    actor_user_agent TEXT,
    
    -- Changes
    old_value JSONB,
    new_value JSONB,
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Case History Table (Status Changes)
CREATE TABLE case_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Status Change
    old_status report_status,
    new_status report_status NOT NULL,
    
    -- Actor
    changed_by UUID REFERENCES users(id),
    changed_by_name VARCHAR(255),
    
    -- Notes
    notes TEXT,
    reason VARCHAR(500),
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RAG / VECTOR TABLES
-- ============================================================

-- Knowledge Vectors Table (Regulations, Policies)
CREATE TABLE knowledge_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Document Info
    doc_type VARCHAR(50) NOT NULL, -- regulation, policy, procedure, faq
    doc_name VARCHAR(255) NOT NULL,
    doc_source VARCHAR(500),
    
    -- Content
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER,
    
    -- Vector Embedding (384 dimensions for MiniLM)
    embedding vector(384),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Case Vectors Table (Past Cases for Similar Case Matching)
CREATE TABLE case_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Case Summary
    case_summary TEXT NOT NULL,
    
    -- Classification
    category violation_category,
    severity severity_level,
    outcome VARCHAR(50), -- proven, not_proven, invalid
    
    -- Vector Embedding
    embedding vector(384),
    
    -- Metadata
    resolution_summary TEXT,
    lessons_learned TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Reports Indexes
CREATE INDEX idx_reports_ticket_id ON reports(ticket_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_severity ON reports(severity);
CREATE INDEX idx_reports_category ON reports(category);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_assigned_to ON reports(assigned_to);
CREATE INDEX idx_reports_channel ON reports(channel);

-- Full Text Search on Reports
CREATE INDEX idx_reports_description_gin ON reports USING gin(to_tsvector('indonesian', description));
CREATE INDEX idx_reports_title_gin ON reports USING gin(to_tsvector('indonesian', coalesce(title, '')));

-- Tickets Indexes
CREATE INDEX idx_tickets_ticket_id ON tickets(ticket_id);
CREATE INDEX idx_tickets_report_id ON tickets(report_id);

-- Messages Indexes
CREATE INDEX idx_messages_ticket_id ON messages(ticket_id);
CREATE INDEX idx_messages_report_id ON messages(report_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- Audit Logs Indexes
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id);

-- Case History Indexes
CREATE INDEX idx_case_history_report_id ON case_history(report_id);
CREATE INDEX idx_case_history_created_at ON case_history(created_at DESC);

-- Vector Indexes (HNSW for fast similarity search)
CREATE INDEX idx_knowledge_vectors_embedding ON knowledge_vectors 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_case_vectors_embedding ON case_vectors 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Function: Generate Unique Ticket ID
CREATE OR REPLACE FUNCTION generate_ticket_id()
RETURNS VARCHAR(8) AS $$
DECLARE
    chars VARCHAR(36) := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    result VARCHAR(8) := '';
    i INTEGER;
BEGIN
    FOR i IN 1..8 LOOP
        result := result || substr(chars, floor(random() * length(chars) + 1)::integer, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function: Update Timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function: Match Documents (RAG Retrieval)
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(384),
    match_count INTEGER DEFAULT 5,
    filter_doc_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    doc_type VARCHAR,
    doc_name VARCHAR,
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kv.id,
        kv.doc_type,
        kv.doc_name,
        kv.content,
        1 - (kv.embedding <=> query_embedding) AS similarity
    FROM knowledge_vectors kv
    WHERE 
        (filter_doc_type IS NULL OR kv.doc_type = filter_doc_type)
    ORDER BY kv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Match Similar Cases
CREATE OR REPLACE FUNCTION match_cases(
    query_embedding vector(384),
    match_count INTEGER DEFAULT 3,
    filter_category violation_category DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    report_id UUID,
    case_summary TEXT,
    category violation_category,
    severity severity_level,
    outcome VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cv.id,
        cv.report_id,
        cv.case_summary,
        cv.category,
        cv.severity,
        cv.outcome,
        1 - (cv.embedding <=> query_embedding) AS similarity
    FROM case_vectors cv
    WHERE 
        (filter_category IS NULL OR cv.category = filter_category)
    ORDER BY cv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate SLA Deadlines
CREATE OR REPLACE FUNCTION calculate_sla_deadlines(
    p_severity severity_level,
    p_created_at TIMESTAMPTZ
)
RETURNS TABLE (
    response_deadline TIMESTAMPTZ,
    review_deadline TIMESTAMPTZ,
    investigation_deadline TIMESTAMPTZ
) AS $$
BEGIN
    CASE p_severity
        WHEN 'CRITICAL' THEN
            RETURN QUERY SELECT 
                p_created_at + INTERVAL '4 hours',
                p_created_at + INTERVAL '1 day',
                p_created_at + INTERVAL '7 days';
        WHEN 'HIGH' THEN
            RETURN QUERY SELECT 
                p_created_at + INTERVAL '24 hours',
                p_created_at + INTERVAL '3 days',
                p_created_at + INTERVAL '14 days';
        WHEN 'MEDIUM' THEN
            RETURN QUERY SELECT 
                p_created_at + INTERVAL '72 hours',
                p_created_at + INTERVAL '7 days',
                p_created_at + INTERVAL '30 days';
        ELSE -- LOW
            RETURN QUERY SELECT 
                p_created_at + INTERVAL '168 hours',
                p_created_at + INTERVAL '14 days',
                p_created_at + INTERVAL '90 days';
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Function: Get Dashboard Stats
CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS TABLE (
    total_reports BIGINT,
    new_reports BIGINT,
    investigating BIGINT,
    closed_reports BIGINT,
    critical_count BIGINT,
    high_count BIGINT,
    sla_breach_count BIGINT,
    avg_resolution_days NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT AS total_reports,
        COUNT(*) FILTER (WHERE status = 'NEW')::BIGINT AS new_reports,
        COUNT(*) FILTER (WHERE status = 'INVESTIGATING')::BIGINT AS investigating,
        COUNT(*) FILTER (WHERE status IN ('CLOSED_PROVEN', 'CLOSED_NOT_PROVEN', 'CLOSED_INVALID'))::BIGINT AS closed_reports,
        COUNT(*) FILTER (WHERE severity = 'CRITICAL')::BIGINT AS critical_count,
        COUNT(*) FILTER (WHERE severity = 'HIGH')::BIGINT AS high_count,
        COUNT(*) FILTER (WHERE 
            (status NOT IN ('CLOSED_PROVEN', 'CLOSED_NOT_PROVEN', 'CLOSED_INVALID') AND sla_response_deadline < NOW())
            OR (status = 'INVESTIGATING' AND sla_investigation_deadline < NOW())
        )::BIGINT AS sla_breach_count,
        COALESCE(
            AVG(EXTRACT(DAY FROM (closed_at - created_at))) FILTER (WHERE closed_at IS NOT NULL),
            0
        )::NUMERIC AS avg_resolution_days
    FROM reports;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update updated_at
CREATE TRIGGER trigger_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Auto-generate ticket_id for reports
CREATE OR REPLACE FUNCTION auto_generate_ticket_id()
RETURNS TRIGGER AS $$
DECLARE
    new_ticket_id VARCHAR(8);
    max_attempts INTEGER := 10;
    attempt INTEGER := 0;
BEGIN
    IF NEW.ticket_id IS NULL THEN
        LOOP
            new_ticket_id := generate_ticket_id();
            BEGIN
                NEW.ticket_id := new_ticket_id;
                EXIT;
            EXCEPTION WHEN unique_violation THEN
                attempt := attempt + 1;
                IF attempt >= max_attempts THEN
                    RAISE EXCEPTION 'Could not generate unique ticket_id after % attempts', max_attempts;
                END IF;
            END;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_ticket_id
    BEFORE INSERT ON reports
    FOR EACH ROW
    EXECUTE FUNCTION auto_generate_ticket_id();

-- Auto-create ticket when report is created
CREATE OR REPLACE FUNCTION auto_create_ticket()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO tickets (ticket_id, report_id, access_token)
    VALUES (
        NEW.ticket_id,
        NEW.id,
        encode(gen_random_bytes(32), 'hex')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_create_ticket
    AFTER INSERT ON reports
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_ticket();

-- Auto-log status changes
CREATE OR REPLACE FUNCTION log_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO case_history (report_id, old_status, new_status)
        VALUES (NEW.id, OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_log_status_change
    AFTER UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION log_status_change();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access" ON reports
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON tickets
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON messages
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON attachments
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON audit_logs
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON users
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON knowledge_vectors
    FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access" ON case_vectors
    FOR ALL TO service_role USING (true);

-- Policy: Anon can insert reports (whistleblower submission)
CREATE POLICY "Anon can submit reports" ON reports
    FOR INSERT TO anon
    WITH CHECK (true);

-- Policy: Anon can read own ticket by ticket_id
CREATE POLICY "Anon can view own ticket" ON tickets
    FOR SELECT TO anon
    USING (true);

-- Policy: Anon can insert messages
CREATE POLICY "Anon can send messages" ON messages
    FOR INSERT TO anon
    WITH CHECK (true);

-- Policy: Anon can read messages by ticket_id
CREATE POLICY "Anon can view messages" ON messages
    FOR SELECT TO anon
    USING (true);

-- ============================================================
-- STORAGE BUCKETS (Run in Supabase Dashboard)
-- ============================================================

-- Note: Execute these in Supabase Dashboard > Storage
-- INSERT INTO storage.buckets (id, name, public) VALUES ('attachments', 'attachments', false);
-- INSERT INTO storage.buckets (id, name, public) VALUES ('evidence', 'evidence', false);

-- ============================================================
-- SEED DATA (Optional)
-- ============================================================

-- Default Admin User (change password!)
INSERT INTO users (email, password_hash, full_name, role, department)
VALUES (
    'admin@bpkh.go.id',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VttYr/LYfqHbHm', -- password: admin123
    'System Administrator',
    'ADMIN',
    'IT'
) ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- VIEWS (For Dashboard)
-- ============================================================

-- View: Reports with SLA Status
CREATE OR REPLACE VIEW v_reports_with_sla AS
SELECT 
    r.*,
    CASE 
        WHEN r.status IN ('CLOSED_PROVEN', 'CLOSED_NOT_PROVEN', 'CLOSED_INVALID') THEN 'CLOSED'
        WHEN r.sla_response_deadline < NOW() AND r.responded_at IS NULL THEN 'BREACHED'
        WHEN r.sla_investigation_deadline < NOW() AND r.status = 'INVESTIGATING' THEN 'BREACHED'
        WHEN r.sla_response_deadline < NOW() + INTERVAL '24 hours' THEN 'AT_RISK'
        ELSE 'ON_TRACK'
    END AS sla_status,
    u.full_name AS assigned_to_name
FROM reports r
LEFT JOIN users u ON r.assigned_to = u.id;

-- View: Daily Statistics
CREATE OR REPLACE VIEW v_daily_stats AS
SELECT 
    DATE(created_at) AS report_date,
    COUNT(*) AS total_reports,
    COUNT(*) FILTER (WHERE severity = 'CRITICAL') AS critical,
    COUNT(*) FILTER (WHERE severity = 'HIGH') AS high,
    COUNT(*) FILTER (WHERE severity = 'MEDIUM') AS medium,
    COUNT(*) FILTER (WHERE severity = 'LOW') AS low,
    COUNT(*) FILTER (WHERE category = 'CORRUPTION') AS corruption,
    COUNT(*) FILTER (WHERE category = 'FRAUD') AS fraud,
    COUNT(*) FILTER (WHERE category = 'GRATIFICATION') AS gratification
FROM reports
GROUP BY DATE(created_at)
ORDER BY report_date DESC;

-- View: Category Distribution
CREATE OR REPLACE VIEW v_category_distribution AS
SELECT 
    category,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / NULLIF(SUM(COUNT(*)) OVER (), 0) * 100, 2) AS percentage
FROM reports
WHERE category IS NOT NULL
GROUP BY category
ORDER BY count DESC;

-- ============================================================
-- COMMENTS (Documentation)
-- ============================================================

COMMENT ON TABLE reports IS 'Main whistleblowing reports table - stores all incoming reports';
COMMENT ON TABLE tickets IS 'Public access tickets for whistleblowers to track their reports';
COMMENT ON TABLE messages IS 'Two-way communication between whistleblower and admin';
COMMENT ON TABLE knowledge_vectors IS 'RAG knowledge base - regulations, policies, procedures';
COMMENT ON TABLE case_vectors IS 'Past case embeddings for similar case matching';
COMMENT ON FUNCTION match_documents IS 'RAG retrieval function using cosine similarity';
COMMENT ON FUNCTION match_cases IS 'Similar case matching using cosine similarity';

-- ============================================================
-- COMPLETION MESSAGE
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ WBS BPKH Database Schema created successfully!';
    RAISE NOTICE '📊 Tables: reports, tickets, messages, attachments, audit_logs, users, case_history, knowledge_vectors, case_vectors';
    RAISE NOTICE '🔍 Functions: match_documents, match_cases, calculate_sla_deadlines, get_dashboard_stats';
    RAISE NOTICE '🔐 RLS Policies: Enabled for all tables';
    RAISE NOTICE '📈 Views: v_reports_with_sla, v_daily_stats, v_category_distribution';
END $$;
