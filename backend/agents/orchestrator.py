"""
WBS BPKH AI - Orchestrator Agent
================================
Main coordinator for multi-agent analysis system.
Implements ISO 37002:2021 compliant workflow.
"""

from groq import Groq
from typing import Dict, Any, Optional
import json
import asyncio
from datetime import datetime
from loguru import logger

from config import settings, VIOLATION_CATEGORIES, SEVERITY_LEVELS
from .intake_agent import IntakeAgent
from .analysis_agent import AnalysisAgent
from .compliance_agent import ComplianceAgent
from .severity_agent import SeverityAgent
from .recommendation_agent import RecommendationAgent
from .summary_agent import SummaryAgent
from .utils import retry_llm_call, truncate_content


class OrchestratorAgent:
    """
    Orchestrator Agent - Coordinates multi-agent analysis workflow
    
    Workflow:
    1. IntakeAgent: Parse 4W+1H from report
    2. AnalysisAgent: Calculate fraud indicators
    3. ComplianceAgent: Check regulation violations
    4. SeverityAgent: Assess risk level
    5. RecommendationAgent: Generate action items
    6. SummaryAgent: Create executive summary
    """
    
    def __init__(self, rag_context: Optional[str] = None):
        """Initialize orchestrator with optional RAG context"""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model
        self.rag_context = rag_context
        
        # Initialize sub-agents
        self.intake_agent = IntakeAgent(self.client, self.model)
        self.analysis_agent = AnalysisAgent(self.client, self.model)
        self.compliance_agent = ComplianceAgent(self.client, self.model)
        self.severity_agent = SeverityAgent(self.client, self.model)
        self.recommendation_agent = RecommendationAgent(self.client, self.model)
        self.summary_agent = SummaryAgent(self.client, self.model)
        
        logger.info("OrchestratorAgent initialized with all sub-agents")
    
    async def analyze_report(
        self,
        report_content: str,
        attachments_text: Optional[str] = None,
        similar_cases: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Main analysis pipeline - coordinates all agents
        
        Args:
            report_content: Original report text
            attachments_text: Extracted text from attachments
            similar_cases: Similar historical cases from RAG
            
        Returns:
            Complete analysis result
        """
        logger.info("Starting multi-agent analysis pipeline")
        
        analysis_result = {
            "analysis_id": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            "analyzed_at": datetime.utcnow().isoformat(),
            "agents_used": [],
            "status": "IN_PROGRESS"
        }
        
        try:
            # Combine report content with attachments and truncate if needed
            full_content = report_content
            if attachments_text:
                full_content += f"\n\n[LAMPIRAN]:\n{attachments_text}"
            full_content = truncate_content(full_content)

            # Step 1: Intake Agent - Parse 4W+1H (must run first)
            logger.info("Step 1: Running IntakeAgent (4W+1H)")
            intake_result = await retry_llm_call(
                lambda: self.intake_agent.parse(full_content)
            )
            analysis_result["intake"] = intake_result
            analysis_result["agents_used"].append("IntakeAgent")

            # Step 2+3: AnalysisAgent + ComplianceAgent in PARALLEL
            # (both depend on intake_result but are independent of each other)
            logger.info("Step 2+3: Running AnalysisAgent & ComplianceAgent in parallel")
            fraud_result, compliance_result = await asyncio.gather(
                retry_llm_call(lambda: self.analysis_agent.analyze(
                    full_content, intake_result
                )),
                retry_llm_call(lambda: self.compliance_agent.check(
                    full_content, intake_result, self.rag_context
                ))
            )
            analysis_result["fraud_analysis"] = fraud_result
            analysis_result["fraud_score"] = fraud_result.get("fraud_score", 0.0)
            analysis_result["agents_used"].append("AnalysisAgent")
            analysis_result["compliance"] = compliance_result
            analysis_result["agents_used"].append("ComplianceAgent")

            # Step 4: Severity Agent - needs both fraud + compliance results
            logger.info("Step 4: Running SeverityAgent")
            severity_result = await retry_llm_call(
                lambda: self.severity_agent.assess(
                    full_content, intake_result, fraud_result, compliance_result
                )
            )
            analysis_result["severity"] = severity_result.get("level", "MEDIUM")
            analysis_result["severity_details"] = severity_result
            analysis_result["agents_used"].append("SeverityAgent")

            # Step 5: Recommendation Agent
            logger.info("Step 5: Running RecommendationAgent")
            recommendation_result = await retry_llm_call(
                lambda: self.recommendation_agent.recommend(
                    full_content, intake_result, fraud_result,
                    compliance_result, severity_result, similar_cases
                )
            )
            analysis_result["recommendations"] = recommendation_result
            analysis_result["agents_used"].append("RecommendationAgent")

            # Step 6: Summary Agent
            logger.info("Step 6: Running SummaryAgent")
            summary_result = await retry_llm_call(
                lambda: self.summary_agent.summarize(
                    full_content, intake_result, fraud_result,
                    compliance_result, severity_result, recommendation_result
                )
            )
            analysis_result["executive_summary"] = summary_result
            analysis_result["agents_used"].append("SummaryAgent")

            # Determine category from compliance result
            analysis_result["category"] = self._determine_category(
                compliance_result,
                intake_result
            )

            # Calculate priority
            analysis_result["priority"] = self._calculate_priority(
                analysis_result["severity"],
                analysis_result["fraud_score"]
            )

            # Similar cases from RAG
            if similar_cases:
                analysis_result["similar_cases"] = similar_cases[:3]

            analysis_result["status"] = "COMPLETED"
            logger.info(f"Analysis completed: Severity={analysis_result['severity']}, Score={analysis_result['fraud_score']:.2f}")
            
        except Exception as e:
            logger.error(f"Analysis pipeline error: {str(e)}")
            analysis_result["status"] = "ERROR"
            analysis_result["error"] = str(e)
        
        return analysis_result
    
    def _determine_category(
        self,
        compliance_result: Dict[str, Any],
        intake_result: Dict[str, Any]
    ) -> str:
        """Determine primary violation category"""
        categories = compliance_result.get("categories", [])
        if categories:
            return categories[0]
        
        # Fallback based on keywords in intake
        what = intake_result.get("what", "").lower()
        
        keyword_mapping = {
            "korupsi": "CORRUPTION",
            "suap": "CORRUPTION",
            "fraud": "FRAUD",
            "penipuan": "FRAUD",
            "gratifikasi": "GRATIFICATION",
            "hadiah": "GRATIFICATION",
            "pengadaan": "PROCUREMENT",
            "tender": "PROCUREMENT",
            "data": "DATA_BREACH",
            "bocor": "DATA_BREACH",
            "etika": "ETHICS",
            "disiplin": "MISCONDUCT"
        }
        
        for keyword, category in keyword_mapping.items():
            if keyword in what:
                return category
        
        return "OTHER"
    
    def _calculate_priority(
        self,
        severity: str,
        fraud_score: float
    ) -> str:
        """Calculate priority based on severity and fraud score"""
        priority_matrix = {
            "CRITICAL": "P1 - Immediate",
            "HIGH": "P2 - Urgent",
            "MEDIUM": "P3 - Normal",
            "LOW": "P4 - Low"
        }
        
        # Upgrade priority if fraud score is very high
        if fraud_score >= 0.8 and severity in ["MEDIUM", "LOW"]:
            return "P2 - Urgent"
        
        return priority_matrix.get(severity, "P3 - Normal")


class QuickAnalyzer:
    """
    Quick single-prompt analyzer for simple cases
    Uses one LLM call instead of multi-agent for efficiency
    """
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model
    
    async def quick_analyze(self, report_content: str) -> Dict[str, Any]:
        """Quick analysis using single comprehensive prompt"""
        
        system_prompt = """Anda adalah AI Analyst untuk Whistleblowing System BPKH.
        
Analisis laporan pelanggaran berikut dan berikan output dalam format JSON:

{
    "what": "Apa yang terjadi (inti pelanggaran)",
    "who": "Siapa yang terlibat",
    "when": "Kapan terjadi",
    "where": "Dimana terjadi",
    "how": "Bagaimana modus operandinya",
    "category": "FRAUD|CORRUPTION|GRATIFICATION|COI|PROCUREMENT|DATA_BREACH|ETHICS|MISCONDUCT|OTHER",
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "fraud_score": 0.0-1.0,
    "compliance_issues": ["regulasi yang dilanggar"],
    "recommended_actions": ["tindakan yang disarankan"],
    "summary": "ringkasan eksekutif dalam 2-3 kalimat"
}

Pertimbangkan:
- Estimasi kerugian keuangan
- Level pejabat yang terlibat
- Kelengkapan bukti
- Dampak terhadap organisasi
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Laporan:\n{report_content}"}
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["analysis_type"] = "QUICK"
            result["analyzed_at"] = datetime.utcnow().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Quick analysis error: {e}")
            return {
                "error": str(e),
                "status": "FAILED"
            }
