"""
WBS BPKH AI - Knowledge Router
===============================
Knowledge base management endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from loguru import logger

from config import GENERIC_ERROR_MESSAGE
from auth import require_role, UserRole, TokenData

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge"])


@router.post("/load")
async def load_knowledge_base(
    request: Request,
    current_user: TokenData = Depends(require_role(UserRole.ADMIN)),
):
    """Load all regulations into knowledge base (Admin only)."""
    try:
        knowledge_loader = request.app.state.knowledge_loader
        results = await knowledge_loader.load_all()
        return {"message": "Knowledge base loaded", "results": results}
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
