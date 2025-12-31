-- ============================================
-- WBS BPKH - Users & Authentication Schema
-- ============================================
-- Jalankan di Supabase SQL Editor

-- Enable UUID extension (jika belum)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUM Types untuk User Roles
-- ============================================

-- User roles berdasarkan ISO 37002:2021
CREATE TYPE user_role AS ENUM (
    'REPORTER',           -- Pelapor (public, anonymous via ticket)
    'INTAKE_OFFICER',     -- Penerima Laporan - telaah awal
    'INVESTIGATOR',       -- Tim Investigasi
    'MANAGER',            -- Pimpinan WBS - keputusan
    'ADMIN'               -- Admin Sistem
);

-- User status
CREATE TYPE user_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'SUSPENDED'
);

-- ============================================
-- Users Table
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Profile
    full_name VARCHAR(255) NOT NULL,
    employee_id VARCHAR(50),           -- NIP/NIK pegawai
    department VARCHAR(100),           -- Unit kerja
    phone VARCHAR(20),

    -- Role & Status
    role user_role NOT NULL DEFAULT 'INTAKE_OFFICER',
    status user_status NOT NULL DEFAULT 'ACTIVE',

    -- Security
    last_login TIMESTAMPTZ,
    login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    must_change_password BOOLEAN DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    -- Indexes
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- ============================================
-- User Sessions Table (untuk tracking)
-- ============================================

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    token_hash VARCHAR(255) NOT NULL,      -- Hashed refresh token
    device_info VARCHAR(500),               -- User agent / device
    ip_address INET,

    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,

    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- ============================================
-- Report Assignments Table
-- ============================================
-- Untuk assign laporan ke investigator tertentu

CREATE TABLE IF NOT EXISTS report_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    assigned_to UUID NOT NULL REFERENCES users(id),
    assigned_by UUID NOT NULL REFERENCES users(id),

    role VARCHAR(50) NOT NULL,             -- 'PRIMARY', 'SECONDARY', 'REVIEWER'
    notes TEXT,

    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    UNIQUE(report_id, assigned_to)
);

-- ============================================
-- Indexes
-- ============================================

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_assignments_report ON report_assignments(report_id);
CREATE INDEX idx_assignments_user ON report_assignments(assigned_to);

-- ============================================
-- Triggers
-- ============================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_users_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_users_timestamp();

-- ============================================
-- Row Level Security (RLS)
-- ============================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_assignments ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access on users" ON users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on sessions" ON user_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on assignments" ON report_assignments
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- Default Admin User (GANTI PASSWORD!)
-- ============================================

-- Password default: Admin@WBS2025 (HARUS DIGANTI!)
-- Hash ini dibuat dengan bcrypt
INSERT INTO users (
    email,
    password_hash,
    full_name,
    role,
    status,
    must_change_password
) VALUES (
    'admin@bpkh.go.id',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferGkVXCGqbu',  -- Admin@WBS2025
    'Administrator WBS',
    'ADMIN',
    'ACTIVE',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- ============================================
-- Sample Users (Opsional - untuk testing)
-- ============================================

-- Intake Officer
INSERT INTO users (email, password_hash, full_name, role, department)
VALUES (
    'intake@bpkh.go.id',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferGkVXCGqbu',
    'Petugas Penerima',
    'INTAKE_OFFICER',
    'Unit Kepatuhan'
) ON CONFLICT (email) DO NOTHING;

-- Investigator
INSERT INTO users (email, password_hash, full_name, role, department)
VALUES (
    'investigator@bpkh.go.id',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferGkVXCGqbu',
    'Tim Investigasi',
    'INVESTIGATOR',
    'Unit Audit Internal'
) ON CONFLICT (email) DO NOTHING;

-- Manager
INSERT INTO users (email, password_hash, full_name, role, department)
VALUES (
    'manager@bpkh.go.id',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferGkVXCGqbu',
    'Kepala Unit WBS',
    'MANAGER',
    'Direktorat Kepatuhan'
) ON CONFLICT (email) DO NOTHING;

-- ============================================
-- Verification Query
-- ============================================
-- SELECT id, email, full_name, role, status FROM users;
