"""
Script untuk reset password admin
Jalankan: python reset_admin.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bcrypt
from supabase import create_client

# Load env
from dotenv import load_dotenv
load_dotenv()

# Generate new hash
new_password = "Admin123!"
truncated = new_password[:72].encode('utf-8')
new_hash = bcrypt.hashpw(truncated, bcrypt.gensalt(rounds=12)).decode('utf-8')

print(f"New password: {new_password}")
print(f"New hash: {new_hash}")

# Connect to Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    print("ERROR: SUPABASE_URL atau SUPABASE_SERVICE_KEY tidak ditemukan di .env")
    sys.exit(1)

print(f"\nConnecting to Supabase: {url[:50]}...")

db = create_client(url, key)

# Check current admin user
print("\nChecking admin user...")
result = db.table("users").select("id, email, password_hash, status, role").eq("email", "admin@bpkh.go.id").execute()

if result.data:
    user = result.data[0]
    print(f"Found user: {user['email']}")
    print(f"Current hash: {user['password_hash'][:50]}...")
    print(f"Status: {user.get('status')}")
    print(f"Role: {user.get('role')}")

    # Update password
    print("\nUpdating password...")
    update_result = db.table("users").update({
        "password_hash": new_hash,
        "status": "ACTIVE",
        "login_attempts": 0,
        "locked_until": None
    }).eq("email", "admin@bpkh.go.id").execute()

    print("Password updated successfully!")
    print(f"\nLogin dengan:")
    print(f"  Email: admin@bpkh.go.id")
    print(f"  Password: {new_password}")
else:
    print("Admin user tidak ditemukan. Membuat baru...")

    insert_result = db.table("users").insert({
        "email": "admin@bpkh.go.id",
        "password_hash": new_hash,
        "full_name": "Administrator",
        "role": "ADMIN",
        "status": "ACTIVE"
    }).execute()

    print("Admin user created!")
    print(f"\nLogin dengan:")
    print(f"  Email: admin@bpkh.go.id")
    print(f"  Password: {new_password}")
