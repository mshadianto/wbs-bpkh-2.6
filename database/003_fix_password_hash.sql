-- ============================================
-- Fix: Update password hash for all default users
-- ============================================
-- Password: Admin@WBS2025
-- Hash sebelumnya tidak cocok (placeholder hash)
-- Jalankan di Supabase SQL Editor

UPDATE users
SET password_hash = '$2b$12$KdBh9vM6yfhBlpq9ZVwAK.U1S8zRXfnwJ/qgp0nQJoioDiW.gFIfG',
    login_attempts = 0,
    locked_until = NULL,
    updated_at = NOW()
WHERE email IN (
    'admin@bpkh.go.id',
    'intake@bpkh.go.id',
    'investigator@bpkh.go.id',
    'manager@bpkh.go.id'
);

-- Verifikasi
SELECT email, full_name, role, status, login_attempts, locked_until
FROM users
WHERE email IN (
    'admin@bpkh.go.id',
    'intake@bpkh.go.id',
    'investigator@bpkh.go.id',
    'manager@bpkh.go.id'
);
