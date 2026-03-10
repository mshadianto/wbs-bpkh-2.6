"""
WBS BPKH AI - Analysis Router
==============================
AI analysis trigger and results endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from loguru import logger

from config import GENERIC_ERROR_MESSAGE
from database import report_repo
from models import AnalysisRequest, FullAnalysisResponse
from auth import require_min_role, UserRole, TokenData
from agents import OrchestratorAgent, QuickAnalyzer
from rag import RAGRetriever

router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])


@router.post("/run", response_model=FullAnalysisResponse)
async def run_analysis(
    request: AnalysisRequest,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """Manually trigger AI analysis for a report (Intake Officer+)."""
    try:
        report = await report_repo.get_by_id(request.report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        rag_retriever = RAGRetriever()
        rag_context = await rag_retriever.retrieve_context(report["description"])
        similar_cases = await rag_retriever.retrieve_similar_cases(report["description"])

        if request.use_full_analysis:
            orchestrator = OrchestratorAgent(rag_context=rag_context)
            analysis = await orchestrator.analyze_report(
                report_content=report["description"],
                similar_cases=similar_cases,
            )
        else:
            quick_analyzer = QuickAnalyzer()
            analysis = await quick_analyzer.quick_analyze(report["description"])

        await report_repo.update_analysis(request.report_id, analysis)
        return FullAnalysisResponse(**analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


@router.get("/{report_id}")
async def get_analysis(
    report_id: str,
    current_user: TokenData = Depends(require_min_role(UserRole.INTAKE_OFFICER)),
):
    """Get analysis results for a report (Intake Officer+)."""
    try:
        report = await report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if not report.get("ai_analysis"):
            raise HTTPException(status_code=404, detail="Analysis not available")

        return report["ai_analysis"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
