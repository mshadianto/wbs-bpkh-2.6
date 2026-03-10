"""
WBS BPKH AI - Background Tasks
===============================
Async background tasks with retry logic.
"""

from datetime import datetime
from loguru import logger

from database import report_repo
from agents import OrchestratorAgent
from rag import RAGRetriever


async def run_ai_analysis(
    report_id: str,
    description: str,
    rag_retriever: RAGRetriever,
    retry_count: int = 0,
):
    """Background task to run AI analysis with exponential backoff retry."""
    MAX_RETRIES = 3
    RETRY_DELAYS = [10, 30, 60]

    try:
        logger.info(
            f"Starting background analysis for report {report_id} "
            f"(attempt {retry_count + 1}/{MAX_RETRIES + 1})"
        )

        rag_context = await rag_retriever.retrieve_context(description)
        similar_cases = await rag_retriever.retrieve_similar_cases(description)

        orchestrator = OrchestratorAgent(rag_context=rag_context)
        analysis = await orchestrator.analyze_report(
            report_content=description,
            similar_cases=similar_cases,
        )

        await report_repo.update_analysis(report_id, analysis)
        logger.info(f"Analysis completed for report {report_id}")

    except Exception as e:
        logger.error(
            f"Background analysis failed for {report_id} "
            f"(attempt {retry_count + 1}): {e}"
        )

        if retry_count < MAX_RETRIES:
            delay = RETRY_DELAYS[retry_count]
            logger.info(
                f"Retrying analysis for {report_id} in {delay}s "
                f"(attempt {retry_count + 2}/{MAX_RETRIES + 1})"
            )
            import asyncio
            await asyncio.sleep(delay)
            await run_ai_analysis(
                report_id, description, rag_retriever, retry_count + 1,
            )
            return

        # All retries exhausted — save error state
        try:
            error_analysis = {
                "status": "ERROR",
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat(),
                "retry_count": retry_count + 1,
            }
            report_repo.db.table("reports").update({
                "ai_analysis": error_analysis,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", report_id).execute()
        except Exception as save_err:
            logger.error(f"Failed to save analysis error state: {save_err}")
