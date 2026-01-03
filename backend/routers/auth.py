"""
WBS BPKH AI - Authentication Router
====================================
Endpoints for user authentication and management.
"""

from fastapi import APIRouter, HTTPException, status, Request, Depends
from typing import Optional
from loguru import logger

from auth import (
    UserLogin, UserRegister, UserResponse, TokenResponse, PasswordChange,
    UserRole, UserStatus,
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token,
    require_auth, require_role, TokenData
)
from database import user_repo
from config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ============== Login ==============

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    """
    Login with email and password.
    Returns JWT access token and refresh token.
    """
    try:
        # Get user by email
        user = await user_repo.get_by_email(credentials.email)
        logger.info(f"Login attempt for: {credentials.email}, user found: {user is not None}, password_len: {len(credentials.password)}")

        if not user:
            logger.warning(f"Login attempt for non-existent user: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email atau password salah"
            )

        # Check if account is locked
        if await user_repo.is_account_locked(user["id"]):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Akun terkunci karena terlalu banyak percobaan login. Coba lagi dalam 30 menit."
            )

        # Check if account is active
        user_status = str(user.get("status", "")).upper()
        if user_status != "ACTIVE":
            logger.warning(f"Inactive account login attempt: {credentials.email}, status: {user_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun tidak aktif. Hubungi administrator."
            )

        # Verify password
        logger.info(f"Hash from DB: {user.get('password_hash', 'MISSING')[:30]}...")
        if not verify_password(credentials.password, user["password_hash"]):
            attempts = await user_repo.increment_login_attempts(user["id"])
            remaining = 5 - attempts

            if remaining > 0:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Email atau password salah. {remaining} percobaan tersisa."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Akun terkunci karena terlalu banyak percobaan login."
                )

        # Update last login
        await user_repo.update_last_login(user["id"])

        # Create tokens - handle role safely
        user_role_str = str(user.get("role", "INTAKE_OFFICER")).upper()
        try:
            user_role = UserRole(user_role_str)
        except ValueError:
            logger.warning(f"Unknown role {user_role_str}, defaulting to INTAKE_OFFICER")
            user_role = UserRole.INTAKE_OFFICER

        user_status_enum = UserStatus(user_status) if user_status in ["ACTIVE", "INACTIVE", "SUSPENDED"] else UserStatus.ACTIVE

        access_token = create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user_role
        )
        refresh_token = create_refresh_token(user_id=user["id"])

        logger.info(f"User logged in: {user['email']} ({user_role})")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_expiry_minutes * 60,
            user=UserResponse(
                id=user["id"],
                email=user["email"],
                full_name=user["full_name"],
                employee_id=user.get("employee_id"),
                department=user.get("department"),
                role=user_role,
                status=user_status_enum,
                last_login=user.get("last_login"),
                created_at=user["created_at"]
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login gagal: {str(e)}"
        )


# ============== Register (Admin Only) ==============

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Register new user (Admin only).
    """
    # Check if email already exists
    existing = await user_repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar"
        )

    # Validate password strength
    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Create user
    user = await user_repo.create({
        "email": user_data.email,
        "password_hash": password_hash,
        "full_name": user_data.full_name,
        "employee_id": user_data.employee_id,
        "department": user_data.department,
        "phone": user_data.phone,
        "role": user_data.role.value,
        "must_change_password": True
    })

    logger.info(f"New user registered by {current_user.email}: {user['email']}")

    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        employee_id=user.get("employee_id"),
        department=user.get("department"),
        role=UserRole(user["role"]),
        status=UserStatus(user["status"]),
        last_login=user.get("last_login"),
        created_at=user["created_at"]
    )


# ============== Token Refresh ==============

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token tidak valid"
        )

    user = await user_repo.get_by_id(payload["sub"])

    if not user or user.get("status") != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan atau tidak aktif"
        )

    # Create new access token
    new_access_token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=UserRole(user["role"])
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiry_minutes * 60
    }


# ============== Get Current User ==============

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: TokenData = Depends(require_auth)):
    """
    Get current authenticated user info.
    """
    user = await user_repo.get_by_id(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )

    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        employee_id=user.get("employee_id"),
        department=user.get("department"),
        role=UserRole(user["role"]),
        status=UserStatus(user["status"]),
        last_login=user.get("last_login"),
        created_at=user["created_at"]
    )


# ============== Change Password ==============

@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: TokenData = Depends(require_auth)
):
    """
    Change current user's password.
    """
    user = await user_repo.get_by_id(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )

    # Verify current password
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password saat ini salah"
        )

    # Validate new password
    is_valid, message = validate_password_strength(data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Check if new password is same as old
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru harus berbeda dengan password lama"
        )

    # Update password
    new_hash = hash_password(data.new_password)
    await user_repo.update_password(current_user.user_id, new_hash)

    logger.info(f"Password changed for user: {current_user.email}")

    return {"message": "Password berhasil diubah"}


# ============== Logout ==============

@router.post("/logout")
async def logout(current_user: TokenData = Depends(require_auth)):
    """
    Logout current user (invalidate token on client side).
    """
    # In a stateless JWT system, logout is handled client-side by removing the token.
    # If you want server-side invalidation, use a token blacklist.
    logger.info(f"User logged out: {current_user.email}")

    return {"message": "Logout berhasil"}


# ============== User Management (Admin) ==============

@router.get("/users")
async def list_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    List all users (Admin only).
    """
    users = await user_repo.list_all(role=role, status=status)

    return {
        "users": [
            {
                "id": u["id"],
                "email": u["email"],
                "full_name": u["full_name"],
                "role": u["role"],
                "status": u["status"],
                "department": u.get("department"),
                "last_login": u.get("last_login"),
                "created_at": u["created_at"]
            }
            for u in users
        ],
        "total": len(users)
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Update user role (Admin only).
    """
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )

    await user_repo.update_role(user_id, new_role.value)

    logger.info(f"User role updated by {current_user.email}: {user['email']} -> {new_role.value}")

    return {"message": f"Role berhasil diubah menjadi {new_role.value}"}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    new_status: UserStatus,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN))
):
    """
    Update user status (Admin only).
    """
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )

    # Prevent deactivating self
    if user_id == current_user.user_id and new_status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menonaktifkan akun sendiri"
        )

    await user_repo.update_status(user_id, new_status.value)

    logger.info(f"User status updated by {current_user.email}: {user['email']} -> {new_status.value}")

    return {"message": f"Status berhasil diubah menjadi {new_status.value}"}
