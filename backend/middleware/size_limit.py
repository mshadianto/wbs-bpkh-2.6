"""
WBS BPKH AI - Request Size Limit Middleware
============================================
Enforces maximum request body size to prevent resource exhaustion.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Reject requests with Content-Length exceeding the configured limit.

    Args:
        app: ASGI application
        max_bytes: Maximum allowed body size in bytes (default 5MB)
    """

    def __init__(self, app, max_bytes: int = 5 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            mb = self.max_bytes // (1024 * 1024)
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body terlalu besar. Maksimal {mb}MB."},
            )
        return await call_next(request)
