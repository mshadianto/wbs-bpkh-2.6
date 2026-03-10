"""
WBS BPKH AI - Security Headers Middleware
==========================================
Adds security headers (CSP, HSTS, X-Frame-Options, etc.) to all responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all HTTP responses."""

    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if not self.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
                "https://cdnjs.cloudflare.com https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' "
                "https://cdn.tailwindcss.com https://fonts.googleapis.com "
                "https://cdnjs.cloudflare.com; "
                "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
                "img-src 'self' data:; "
                "connect-src 'self'"
            )

        return response
