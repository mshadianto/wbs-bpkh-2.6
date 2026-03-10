"""
WBS BPKH AI - User Repository
==============================
User CRUD, authentication, and session management.
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from .client import SupabaseDB


class UserRepository:
    """Repository for User operations."""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "users"

    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user."""
        record = {
            "id": str(uuid.uuid4()),
            "email": user_data["email"].lower(),
            "password_hash": user_data["password_hash"],
            "full_name": user_data["full_name"],
            "employee_id": user_data.get("employee_id"),
            "department": user_data.get("department"),
            "phone": user_data.get("phone"),
            "role": user_data.get("role", "INTAKE_OFFICER"),
            "status": "ACTIVE",
            "must_change_password": user_data.get("must_change_password", False),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        result = self.db.table(self.table).insert(record).execute()
        logger.info(f"Created user: {record['email']}")
        return result.data[0] if result.data else record

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        result = self.db.table(self.table)\
            .select("*").eq("email", email.lower()).execute()
        return result.data[0] if result.data else None

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        result = self.db.table(self.table)\
            .select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    async def update_last_login(self, user_id: str) -> None:
        """Update last login timestamp."""
        self.db.table(self.table).update({
            "last_login": datetime.utcnow().isoformat(),
            "login_attempts": 0,
        }).eq("id", user_id).execute()

    async def increment_login_attempts(self, user_id: str) -> int:
        """Increment failed login attempts (atomic RPC with fallback)."""
        try:
            result = self.db.rpc(
                "increment_login_attempts", {"p_user_id": user_id},
            ).execute()
            if result.data:
                data = result.data if isinstance(result.data, dict) else (
                    result.data[0] if result.data else {}
                )
                return data.get("attempts", 0)
        except Exception as e:
            logger.warning(f"Atomic increment RPC failed, using fallback: {e}")

        user = await self.get_by_id(user_id)
        if not user:
            return 0

        attempts = (user.get("login_attempts") or 0) + 1
        update_data = {"login_attempts": attempts}

        if attempts >= 5:
            lock_until = datetime.utcnow() + timedelta(minutes=30)
            update_data["locked_until"] = lock_until.isoformat()

        self.db.table(self.table).update(update_data)\
            .eq("id", user_id).execute()
        return attempts

    async def is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked."""
        user = await self.get_by_id(user_id)
        if not user or not user.get("locked_until"):
            return False
        locked_until = datetime.fromisoformat(user["locked_until"].replace("Z", "+00:00"))
        return datetime.utcnow().replace(tzinfo=locked_until.tzinfo) < locked_until

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """Update user password."""
        result = self.db.table(self.table).update({
            "password_hash": password_hash,
            "password_changed_at": datetime.utcnow().isoformat(),
            "must_change_password": False,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()
        return bool(result.data)

    async def update_status(self, user_id: str, status: str) -> bool:
        """Update user status."""
        result = self.db.table(self.table).update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()
        return bool(result.data)

    async def update_role(self, user_id: str, role: str) -> bool:
        """Update user role."""
        result = self.db.table(self.table).update({
            "role": role,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()
        return bool(result.data)

    async def list_all(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List all users with filters."""
        query = self.db.table(self.table).select("*")
        if role:
            query = query.eq("role", role)
        if status:
            query = query.eq("status", status)
        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)
        result = query.execute()
        return result.data or []

    async def delete(self, user_id: str) -> bool:
        """Soft delete user by setting status to INACTIVE."""
        return await self.update_status(user_id, "INACTIVE")

    async def set_reset_token(self, user_id: str, token: str, expires: datetime) -> bool:
        """Set password reset token and expiry."""
        result = self.db.table(self.table).update({
            "password_reset_token": token,
            "password_reset_expires": expires.isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()
        return bool(result.data)

    async def get_by_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user by password reset token (only if not expired)."""
        result = self.db.table(self.table)\
            .select("*").eq("password_reset_token", token)\
            .gte("password_reset_expires", datetime.utcnow().isoformat())\
            .execute()
        return result.data[0] if result.data else None

    async def clear_reset_token(self, user_id: str) -> bool:
        """Clear password reset token after use."""
        result = self.db.table(self.table).update({
            "password_reset_token": None,
            "password_reset_expires": None,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()
        return bool(result.data)


class SessionRepository:
    """Repository for User Session operations."""

    def __init__(self):
        self.db = SupabaseDB.get_client()
        self.table = "user_sessions"

    async def create(
        self,
        user_id: str,
        token_hash: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Create new session."""
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=7)

        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "token_hash": token_hash,
            "device_info": device_info,
            "ip_address": ip_address,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        result = self.db.table(self.table).insert(record).execute()
        return result.data[0] if result.data else record

    async def revoke(self, session_id: str) -> bool:
        """Revoke a session."""
        result = self.db.table(self.table)\
            .update({"revoked_at": datetime.utcnow().isoformat()})\
            .eq("id", session_id).execute()
        return bool(result.data)

    async def revoke_all_for_user(self, user_id: str) -> bool:
        """Revoke all sessions for a user."""
        result = self.db.table(self.table)\
            .update({"revoked_at": datetime.utcnow().isoformat()})\
            .eq("user_id", user_id).is_("revoked_at", "null").execute()
        return bool(result.data)
