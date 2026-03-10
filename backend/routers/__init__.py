"""
WBS BPKH AI - API Routers
"""

from .auth import router as auth_router
from .webhooks import router as webhooks_router
from .reports import router as reports_router
from .tickets import router as tickets_router
from .analysis import router as analysis_router
from .dashboard import router as dashboard_router
from .investigation import router as investigation_router
from .reference import router as reference_router
from .knowledge import router as knowledge_router

__all__ = [
    "auth_router",
    "webhooks_router",
    "reports_router",
    "tickets_router",
    "analysis_router",
    "dashboard_router",
    "investigation_router",
    "reference_router",
    "knowledge_router",
]
