-- ============================================================
-- WBS BPKH v2.6 - FULL DATABASE SETUP
-- ============================================================
-- Gabungan semua migration scripts untuk fresh Supabase setup.
-- Jalankan di Supabase SQL Editor (satu kali).
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE report_status AS ENUM (
    'NEW', 'REVIEWING', 'NEED_INFO', 'INVESTIGATING',
    'HOLD', 'ESCALATED',
    'CLOSED_PROVEN', 'CLOSED_NOT_PROVEN', 'CLOSED_INVALID'
);

CREATE TYPE severity_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

CREATE TYPE violation_category AS ENUM (
    'FRAUD', 'CORRUPTION', 'GRATIFICATION', 'COI',
    'PROCUREMENT', 'DATA_BREACH', 'ETHICS', 'MISCONDUCT', 'OTHER'
);

CREATE TYPE report_channel AS ENUM (
    'WEB', 'EMAIL', 'WHATSAPP', 'HOTLINE', 'LETTER', 'OTHER'
);

CREATE TYPE sender_type AS ENUM ('REPORTER', 'SYSTEM', 'ADMIN', 'MANAGER');

CREATE TYPE user_role AS ENUM (
    'REPORTER', 'INTAKE_OFFICER', 'INVESTIGATOR', 'MANAGER', 'ADMIN'
);

CREATE TYPE user_status AS ENUM ('ACTIVE', 'INACTIVE', 'SUSPENDED');

-- ============================================================
-- TABLES
-- ============================================================

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    employee_id VARCHAR(50),
    department VARCHAR(100),
    phone VARCHAR(20),
    role user_role NOT NULL DEFAULT 'INTAKE_OFFICER',
    status user_status NOT NULL DEFAULT 'ACTIVE',
    last_login TIMESTAMPTZ,
    login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    must_change_password BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- User Sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    device_info VARCHAR(500),
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- Reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id VARCHAR(8) UNIQUE NOT NULL,
    reporter_name VARCHAR(255),
    reporter_email VARCHAR(255),
    reporter_phone VARCHAR(50),
    reporter_identity_hash VARCHAR(64),
    is_anonymous BOOLEAN DEFAULT FALSE,
    title VARCHAR(500),
    description TEXT NOT NULL,
    incident_date DATE,
    incident_location VARCHAR(500),
    involved_parties TEXT[],
    evidence_description TEXT,
    channel report_channel NOT NULL DEFAULT 'WEB',
    source_reference VARCHAR(255),
    category violation_category,
    severity severity_level,
    fraud_score DECIMAL(3,2),
    priority VARCHAR(20),
    status report_status DEFAULT 'NEW',
    assigned_to UUID REFERENCES users(id),
    escalated_to UUID REFERENCES users(id),
    sla_response_deadline TIMESTAMPTZ,
    sla_review_deadline TIMESTAMPTZ,
    sla_investigation_deadline TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    ai_analysis JSONB,
    intake_analysis JSONB,
    fraud_analysis JSONB,
    compliance_analysis JSONB,
    severity_analysis JSONB,
    recommendations JSONB,
    executive_summary TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    CONSTRAINT valid_fraud_score CHECK (fraud_score >= 0 AND fraud_score <= 1)
);

-- Tickets (public access for whistleblowers)
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id VARCHAR(8) UNIQUE NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    access_token VARCHAR(64) NOT NULL,
    access_token_hash VARCHAR(128),
    public_status VARCHAR(50) DEFAULT 'Diterima',
    last_message_at TIMESTAMPTZ,
    unread_count_reporter INTEGER DEFAULT 0,
    unread_count_admin INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages (two-way communication)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id VARCHAR(8) NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    sender_type sender_type NOT NULL,
    sender_id UUID,
    sender_name VARCHAR(255),
    content TEXT NOT NULL,
    has_attachments BOOLEAN DEFAULT FALSE,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attachments
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size INTEGER,
    mime_type VARCHAR(100),
    storage_path VARCHAR(1000),
    storage_bucket VARCHAR(100) DEFAULT 'attachments',
    is_encrypted BOOLEAN DEFAULT TRUE,
    checksum VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by UUID REFERENCES users(id)
);

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    action_details TEXT,
    actor_type VARCHAR(50),
    actor_id UUID,
    actor_email VARCHAR(255),
    actor_ip VARCHAR(45),
    actor_user_agent TEXT,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Case History (status changes)
CREATE TABLE case_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    old_status report_status,
    new_status report_status NOT NULL,
    changed_by UUID REFERENCES users(id),
    changed_by_name VARCHAR(255),
    notes TEXT,
    reason VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Report Assignments
CREATE TABLE report_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    assigned_to UUID NOT NULL REFERENCES users(id),
    assigned_by UUID NOT NULL REFERENCES users(id),
    role VARCHAR(50) NOT NULL,
    notes TEXT,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(report_id, assigned_to)
);

-- Knowledge Vectors (RAG)
CREATE TABLE knowledge_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_type VARCHAR(50) NOT NULL,
    doc_name VARCHAR(255) NOT NULL,
    doc_source VARCHAR(500),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Case Vectors (similar case matching)
CREATE TABLE case_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    case_summary TEXT NOT NULL,
    category violation_category,
    severity severity_level,
    outcome VARCHAR(50),
    embedding vector(384),
    resolution_summary TEXT,
    lessons_learned TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

-- Sessions
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);

-- Reports
CREATE INDEX idx_reports_ticket_id ON reports(ticket_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_severity ON reports(severity);
CREATE INDEX idx_reports_category ON reports(category);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_assigned_to ON reports(assigned_to);
CREATE INDEX idx_reports_channel ON reports(channel);
CREATE INDEX idx_reports_description_gin ON reports USING gin(to_tsvector('indonesian', description));
CREATE INDEX idx_reports_title_gin ON reports USING gin(to_tsvector('indonesian', coalesce(title, '')));

-- Tickets
CREATE INDEX idx_tickets_ticket_id ON tickets(ticket_id);
CREATE INDEX idx_tickets_report_id ON tickets(report_id);

-- Messages
CREATE INDEX idx_messages_ticket_id ON messages(ticket_id);
CREATE INDEX idx_messages_report_id ON messages(report_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- Audit Logs
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id);

-- Case History
CREATE INDEX idx_case_history_report_id ON case_history(report_id);
CREATE INDEX idx_case_history_created_at ON case_history(created_at DESC);

-- Assignments
CREATE INDEX idx_assignments_report ON report_assignments(report_id);
CREATE INDEX idx_assignments_user ON report_assignments(assigned_to);

-- Vector Indexes (HNSW)
CREATE INDEX idx_knowledge_vectors_embedding ON knowledge_vectors
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_case_vectors_embedding ON case_vectors
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Generate Unique Ticket ID
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

-- Update Timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Match Documents (RAG Retrieval)
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
        kv.id, kv.doc_type, kv.doc_name, kv.content,
        1 - (kv.embedding <=> query_embedding) AS similarity
    FROM knowledge_vectors kv
    WHERE (filter_doc_type IS NULL OR kv.doc_type = filter_doc_type)
    ORDER BY kv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Match Similar Cases
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
        cv.id, cv.report_id, cv.case_summary,
        cv.category, cv.severity, cv.outcome,
        1 - (cv.embedding <=> query_embedding) AS similarity
    FROM case_vectors cv
    WHERE (filter_category IS NULL OR cv.category = filter_category)
    ORDER BY cv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Calculate SLA Deadlines
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
        ELSE
            RETURN QUERY SELECT
                p_created_at + INTERVAL '168 hours',
                p_created_at + INTERVAL '14 days',
                p_created_at + INTERVAL '90 days';
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Dashboard Stats
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
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE status = 'NEW')::BIGINT,
        COUNT(*) FILTER (WHERE status = 'INVESTIGATING')::BIGINT,
        COUNT(*) FILTER (WHERE status IN ('CLOSED_PROVEN', 'CLOSED_NOT_PROVEN', 'CLOSED_INVALID'))::BIGINT,
        COUNT(*) FILTER (WHERE severity = 'CRITICAL')::BIGINT,
        COUNT(*) FILTER (WHERE severity = 'HIGH')::BIGINT,
        COUNT(*) FILTER (WHERE
            (status NOT IN ('CLOSED_PROVEN', 'CLOSED_NOT_PROVEN', 'CLOSED_INVALID') AND sla_response_deadline < NOW())
            OR (status = 'INVESTIGATING' AND sla_investigation_deadline < NOW())
        )::BIGINT,
        COALESCE(
            AVG(EXTRACT(DAY FROM (closed_at - created_at))) FILTER (WHERE closed_at IS NOT NULL),
            0
        )::NUMERIC
    FROM reports;
END;
$$ LANGUAGE plpgsql;

-- Atomic Login Attempt Increment (prevents TOCTOU race condition)
CREATE OR REPLACE FUNCTION increment_login_attempts(p_user_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_attempts INT;
    v_locked_until TIMESTAMPTZ;
BEGIN
    UPDATE users
    SET login_attempts = login_attempts + 1,
        locked_until = CASE
            WHEN login_attempts + 1 >= 5
            THEN NOW() + INTERVAL '30 minutes'
            ELSE locked_until
        END,
        updated_at = NOW()
    WHERE id = p_user_id
    RETURNING login_attempts, locked_until
    INTO v_attempts, v_locked_until;

    RETURN json_build_object(
        'attempts', COALESCE(v_attempts, 0),
        'locked_until', v_locked_until
    );
END;
$$;

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE TRIGGER trigger_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Auto-generate ticket_id
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
    FOR EACH ROW EXECUTE FUNCTION auto_generate_ticket_id();

-- Auto-create ticket on report insert
CREATE OR REPLACE FUNCTION auto_create_ticket()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO tickets (ticket_id, report_id, access_token)
    VALUES (NEW.ticket_id, NEW.id, encode(gen_random_bytes(32), 'hex'));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_create_ticket
    AFTER INSERT ON reports
    FOR EACH ROW EXECUTE FUNCTION auto_create_ticket();

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
    FOR EACH ROW EXECUTE FUNCTION log_status_change();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_vectors ENABLE ROW LEVEL SECURITY;

-- Service role full access
CREATE POLICY "Service role full access" ON reports FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON tickets FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON messages FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON attachments FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON audit_logs FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON users FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON user_sessions FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON report_assignments FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON knowledge_vectors FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON case_vectors FOR ALL TO service_role USING (true);

-- Anon policies (whistleblower access)
CREATE POLICY "Anon can submit reports" ON reports FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Anon can view own ticket" ON tickets FOR SELECT TO anon USING (true);
CREATE POLICY "Anon can send messages" ON messages FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Anon can view messages" ON messages FOR SELECT TO anon USING (true);

-- ============================================================
-- VIEWS
-- ============================================================

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
-- SEED DATA: Default Users
-- ============================================================
-- Password: Admin@WBS2025 (GANTI di production!)

INSERT INTO users (email, password_hash, full_name, role, status, department, must_change_password)
VALUES
    ('admin@bpkh.go.id', '$2b$12$KdBh9vM6yfhBlpq9ZVwAK.U1S8zRXfnwJ/qgp0nQJoioDiW.gFIfG', 'Administrator WBS', 'ADMIN', 'ACTIVE', 'IT', TRUE),
    ('intake@bpkh.go.id', '$2b$12$KdBh9vM6yfhBlpq9ZVwAK.U1S8zRXfnwJ/qgp0nQJoioDiW.gFIfG', 'Petugas Penerima', 'INTAKE_OFFICER', 'ACTIVE', 'Unit Kepatuhan', FALSE),
    ('investigator@bpkh.go.id', '$2b$12$KdBh9vM6yfhBlpq9ZVwAK.U1S8zRXfnwJ/qgp0nQJoioDiW.gFIfG', 'Tim Investigasi', 'INVESTIGATOR', 'ACTIVE', 'Unit Audit Internal', FALSE),
    ('manager@bpkh.go.id', '$2b$12$KdBh9vM6yfhBlpq9ZVwAK.U1S8zRXfnwJ/qgp0nQJoioDiW.gFIfG', 'Kepala Unit WBS', 'MANAGER', 'ACTIVE', 'Direktorat Kepatuhan', FALSE)
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- TABLE COMMENTS
-- ============================================================

COMMENT ON TABLE reports IS 'Main whistleblowing reports table';
COMMENT ON TABLE tickets IS 'Public access tickets for whistleblowers';
COMMENT ON TABLE messages IS 'Two-way communication between whistleblower and admin';
COMMENT ON TABLE knowledge_vectors IS 'RAG knowledge base - regulations, policies, procedures';
COMMENT ON TABLE case_vectors IS 'Past case embeddings for similar case matching';
COMMENT ON FUNCTION match_documents IS 'RAG retrieval function using cosine similarity';
COMMENT ON FUNCTION match_cases IS 'Similar case matching using cosine similarity';

-- ============================================================
-- DONE
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'WBS BPKH v2.6 Database setup complete!';
    RAISE NOTICE 'Tables: users, user_sessions, reports, tickets, messages, attachments, audit_logs, case_history, report_assignments, knowledge_vectors, case_vectors';
    RAISE NOTICE 'Functions: match_documents, match_cases, calculate_sla_deadlines, get_dashboard_stats, increment_login_attempts';
    RAISE NOTICE 'Default users: admin@bpkh.go.id, intake@bpkh.go.id, investigator@bpkh.go.id, manager@bpkh.go.id';
    RAISE NOTICE 'Password: Admin@WBS2025';
END $$;
