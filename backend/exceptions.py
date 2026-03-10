"""
WBS BPKH AI - Custom Exceptions
================================
Domain-specific exceptions for standardized error handling.
"""

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Resource not found."""
    def __init__(self, resource: str = "Resource", detail: str = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail or f"{resource} tidak ditemukan",
        )


class ForbiddenError(HTTPException):
    """Insufficient permissions."""
    def __init__(self, detail: str = "Akses ditolak"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestError(HTTPException):
    """Invalid request data."""
    def __init__(self, detail: str = "Request tidak valid"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ConflictError(HTTPException):
    """Resource conflict (e.g., duplicate)."""
    def __init__(self, detail: str = "Konflik data"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InvalidTransitionError(BadRequestError):
    """Invalid status transition."""
    def __init__(self, current: str, target: str, allowed: list[str]):
        allowed_str = ", ".join(allowed) if allowed else "tidak ada (status final)"
        super().__init__(
            detail=f"Transisi status tidak valid: {current} → {target}. "
                   f"Status yang diperbolehkan: {allowed_str}",
        )
