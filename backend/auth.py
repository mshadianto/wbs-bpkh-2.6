"""
WBS BPKH AI - Authentication Module
====================================
JWT-based authentication with role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, EmailStr
from loguru import logger

from config import settings


# ============== Enums ==============

class UserRole(str, Enum):
    REPORTER = "REPORTER"
    INTAKE_OFFICER = "INTAKE_OFFICER"
    INVESTIGATOR = "INVESTIGATOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


# ============== Role Hierarchy ==============

# Higher number = more permissions
ROLE_HIERARCHY = {
    UserRole.REPORTER: 0,
    UserRole.INTAKE_OFFICER: 1,
    UserRole.INVESTIGATOR: 2,
    UserRole.MANAGER: 3,
    UserRole.ADMIN: 4,
}


# ============== Pydantic Models ==============

class TokenData(BaseModel):
    user_id: str
    email: str
    role: UserRole
    exp: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.INTAKE_OFFICER


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    employee_id: Optional[str]
    department: Optional[str]
    role: UserRole
    status: UserStatus
    last_login: Optional[datetime]
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ============== Password Hashing ==============

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    # bcrypt has 72 byte limit - truncate to be safe
    truncated_password = (password[:72] if password else "").encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(truncated_password, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        # bcrypt has 72 byte limit - truncate to be safe
        truncated_password = (plain_password[:72] if plain_password else "").encode('utf-8')

        # Validate hash format
        if not hashed_password or not hashed_password.startswith('$2'):
            logger.error(f"Invalid hash format")
            return False

        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(truncated_password, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============== JWT Token ==============

def create_access_token(
    user_id: str,
    email: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiry_minutes)

    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expire,
        "type": "access"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token (longer expiry)"""
    expire = datetime.utcnow() + timedelta(days=7)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# ============== Security Dependency ==============

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[TokenData]:
    """
    Get current user from JWT token.
    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipe token tidak valid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(
        user_id=payload["sub"],
        email=payload["email"],
        role=UserRole(payload["role"]),
        exp=datetime.fromtimestamp(payload["exp"])
    )


async def require_auth(
    user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Require authentication - raises if not logged in"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ============== Role-Based Access Control ==============

class RoleChecker:
    """
    Dependency for checking user roles.

    Usage:
        @app.get("/admin", dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
        async def admin_only():
            ...
    """

    def __init__(self, allowed_roles: List[UserRole], require_any: bool = True):
        """
        Args:
            allowed_roles: List of roles that can access
            require_any: If True, user needs ANY of the roles. If False, needs ALL.
        """
        self.allowed_roles = allowed_roles
        self.require_any = require_any

    async def __call__(
        self,
        user: TokenData = Depends(require_auth)
    ) -> TokenData:
        if self.require_any:
            # User needs at least one of the allowed roles
            if user.role not in self.allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Akses ditolak. Role yang diperlukan: {[r.value for r in self.allowed_roles]}"
                )
        return user


def require_role(*roles: UserRole):
    """
    Decorator-style dependency for role checking.

    Usage:
        @app.get("/admin")
        async def admin_only(user: TokenData = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def role_checker(
        user: TokenData = Depends(require_auth)
    ) -> TokenData:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Role yang diperlukan: {[r.value for r in roles]}"
            )
        return user
    return role_checker


def require_min_role(min_role: UserRole):
    """
    Require minimum role level based on hierarchy.

    Usage:
        @app.get("/reports")
        async def view_reports(user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER))):
            ...
    """
    async def role_checker(
        user: TokenData = Depends(require_auth)
    ) -> TokenData:
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Minimal role: {min_role.value}"
            )
        return user
    return role_checker


# ============== Permission Helpers ==============

def can_view_report(user: TokenData, report: dict) -> bool:
    """Check if user can view a specific report"""
    # Admin and Manager can view all
    if user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return True

    # Investigators can view assigned reports
    if user.role == UserRole.INVESTIGATOR:
        # Check if assigned (would need to query assignments)
        return True  # Simplified for now

    # Intake officers can view new/reviewing reports
    if user.role == UserRole.INTAKE_OFFICER:
        return report.get("status") in ["NEW", "REVIEWING", "NEED_INFO"]

    return False


def can_update_status(user: TokenData, current_status: str, new_status: str) -> bool:
    """Check if user can update report status"""
    status_transitions = {
        UserRole.INTAKE_OFFICER: {
            "NEW": ["REVIEWING", "NEED_INFO", "CLOSED_INVALID"],
            "REVIEWING": ["NEED_INFO", "INVESTIGATING"],
            "NEED_INFO": ["REVIEWING"],
        },
        UserRole.INVESTIGATOR: {
            "INVESTIGATING": ["HOLD", "ESCALATED", "CLOSED_PROVEN", "CLOSED_NOT_PROVEN"],
            "HOLD": ["INVESTIGATING"],
        },
        UserRole.MANAGER: {
            # Manager can do any transition
            "*": ["*"]
        },
        UserRole.ADMIN: {
            "*": ["*"]
        }
    }

    allowed = status_transitions.get(user.role, {})

    # Check wildcard
    if "*" in allowed:
        return True

    # Check specific transition
    allowed_next = allowed.get(current_status, [])
    return new_status in allowed_next


# ============== Utility Functions ==============

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password minimal 8 karakter"

    if len(password) > 72:
        return False, "Password maksimal 72 karakter (batas bcrypt)"

    if not any(c.isupper() for c in password):
        return False, "Password harus mengandung huruf besar"

    if not any(c.islower() for c in password):
        return False, "Password harus mengandung huruf kecil"

    if not any(c.isdigit() for c in password):
        return False, "Password harus mengandung angka"

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password harus mengandung karakter spesial"

    return True, "Password valid"
