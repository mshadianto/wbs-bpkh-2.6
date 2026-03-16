"""
Seed UAT Users for WBS BPKH AI
================================
Creates test users for User Acceptance Testing (UAT).
Run from project root: python scripts/seed_uat_users.py

All passwords meet requirements: 8+ chars, uppercase, lowercase, digit, special char.
"""

import sys
import os
import uuid
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import settings
from auth import hash_password
from supabase import create_client

UAT_USERS = [
    {
        "email": "admin@bpkh.go.id",
        "password": "Admin@Uat2026!",
        "full_name": "Admin UAT",
        "employee_id": "BPKH-001",
        "department": "IT & Sistem Informasi",
        "phone": "081200000001",
        "role": "ADMIN",
    },
    {
        "email": "manager@bpkh.go.id",
        "password": "Manager@Uat2026!",
        "full_name": "Manager UAT",
        "employee_id": "BPKH-002",
        "department": "Divisi Kepatuhan",
        "phone": "081200000002",
        "role": "MANAGER",
    },
    {
        "email": "investigator@bpkh.go.id",
        "password": "Investigator@Uat2026!",
        "full_name": "Investigator UAT",
        "employee_id": "BPKH-003",
        "department": "Divisi Investigasi",
        "phone": "081200000003",
        "role": "INVESTIGATOR",
    },
    {
        "email": "investigator2@bpkh.go.id",
        "password": "Investigator2@Uat2026!",
        "full_name": "Investigator 2 UAT",
        "employee_id": "BPKH-004",
        "department": "Divisi Investigasi",
        "phone": "081200000004",
        "role": "INVESTIGATOR",
    },
    {
        "email": "intake@bpkh.go.id",
        "password": "Intake@Uat2026!",
        "full_name": "Intake Officer UAT",
        "employee_id": "BPKH-005",
        "department": "Divisi Pengaduan",
        "phone": "081200000005",
        "role": "INTAKE_OFFICER",
    },
    {
        "email": "intake2@bpkh.go.id",
        "password": "Intake2@Uat2026!",
        "full_name": "Intake Officer 2 UAT",
        "employee_id": "BPKH-006",
        "department": "Divisi Pengaduan",
        "phone": "081200000006",
        "role": "INTAKE_OFFICER",
    },
]


def seed_users():
    """Insert UAT users into Supabase."""
    client = create_client(settings.supabase_url, settings.supabase_service_key)

    created = 0
    skipped = 0

    for user in UAT_USERS:
        # Check if user already exists
        existing = client.table("users").select("id").eq("email", user["email"].lower()).execute()
        if existing.data:
            print(f"  SKIP  {user['email']} (sudah ada)")
            skipped += 1
            continue

        record = {
            "id": str(uuid.uuid4()),
            "email": user["email"].lower(),
            "password_hash": hash_password(user["password"]),
            "full_name": user["full_name"],
            "employee_id": user["employee_id"],
            "department": user["department"],
            "phone": user["phone"],
            "role": user["role"],
            "status": "ACTIVE",
            "must_change_password": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            client.table("users").insert(record).execute()
            print(f"  OK    {user['email']} ({user['role']})")
            created += 1
        except Exception as e:
            print(f"  ERROR {user['email']}: {e}")

    print(f"\nSelesai: {created} dibuat, {skipped} dilewati")


if __name__ == "__main__":
    print("=" * 60)
    print("  Seed UAT Users - WBS BPKH AI")
    print("=" * 60)
    print()
    seed_users()
    print()
    print("=" * 60)
    print("  DAFTAR AKUN UAT")
    print("=" * 60)
    print()
    print(f"{'Role':<18} {'Email':<30} {'Password'}")
    print("-" * 78)
    for u in UAT_USERS:
        print(f"{u['role']:<18} {u['email']:<30} {u['password']}")
    print()
