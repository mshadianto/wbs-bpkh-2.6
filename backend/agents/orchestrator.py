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
from .skill_agent import SkillAgent
from .audit_agent import AuditAgent
from .utils import retry_llm_call, truncate_content, AgentProcessingError


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
    7. SkillAgent: Verify grounding & detect hallucinations
    8. AuditAgent: Audit consistency & detect bias
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
        self.skill_agent = SkillAgent(self.client, self.model)
        self.audit_agent = AuditAgent(self.client, self.model)

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

            failed_agents = []

            # ── Only run IntakeAgent (4W+1H) ──
            # Severity & fraud score are excluded from automated analysis
            # and will be determined manually by the investigation team.

            # Step 1: Intake Agent - Parse 4W+1H
            logger.info("Step 1: Running IntakeAgent (4W+1H)")
            intake_result = await self._run_agent_step(
                "IntakeAgent",
                lambda: self.intake_agent.parse(full_content),
                {"agent": "IntakeAgent", "status": "ERROR",
                 "what": {"violation_type": "Error parsing", "description": ""},
                 "who": {"reported_parties": []}, "when": {"incident_date": "Unknown"},
                 "where": {"location": "Unknown"}, "how": {"modus_operandi": "Unknown"},
                 "completeness_score": 0.0},
                failed_agents
            )
            analysis_result["intake"] = intake_result
            analysis_result["agents_used"].append("IntakeAgent")

            # Step 2: ComplianceAgent - Check regulation violations
            logger.info("Step 2: Running ComplianceAgent")
            compliance_result = await self._run_agent_step(
                "ComplianceAgent",
                lambda: self.compliance_agent.check(full_content, intake_result, self.rag_context),
                {"agent": "ComplianceAgent", "status": "ERROR",
                 "categories": ["OTHER"], "potential_violations": [],
                 "confidence_level": "LOW"},
                failed_agents
            )
            analysis_result["compliance"] = compliance_result
            analysis_result["agents_used"].append("ComplianceAgent")

            # Determine category from compliance + intake
            analysis_result["category"] = self._determine_category(
                compliance_result,
                intake_result
            )

            # Similar cases from RAG
            if similar_cases:
                analysis_result["similar_cases"] = similar_cases[:3]

            # Determine final status
            analysis_result["failed_agents"] = failed_agents
            if not failed_agents:
                analysis_result["status"] = "COMPLETED"
            elif len(failed_agents) == 1:
                analysis_result["status"] = "PARTIAL"
            else:
                analysis_result["status"] = "DEGRADED"

            logger.info(
                f"Analysis {'completed' if not failed_agents else 'completed with failures'}: "
                f"4W+1H parsed, category={analysis_result.get('category')}"
                f"{', Failed=' + str(failed_agents) if failed_agents else ''}"
            )

        except Exception as e:
            logger.error(f"Analysis pipeline error: {str(e)}")
            analysis_result["status"] = "ERROR"
            analysis_result["error"] = str(e)

        return analysis_result

    async def _run_agent_step(
        self,
        agent_name: str,
        agent_call,
        fallback_data: dict,
        failed_agents: list,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """Run a single agent step with error handling and timeout.

        LLM API errors trigger retries via retry_llm_call.
        AgentProcessingError (JSON parse failures) use fallback data.
        All other errors after retry exhaustion use fallback data.
        """
        try:
            return await asyncio.wait_for(
                retry_llm_call(agent_call),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"{agent_name} timed out after {timeout_seconds}s")
            failed_agents.append(agent_name)
            fallback_data["error"] = f"Timeout after {timeout_seconds}s"
            return fallback_data
        except AgentProcessingError as e:
            logger.warning(f"{agent_name} processing failed, using fallback: {e}")
            failed_agents.append(agent_name)
            return e.fallback_data
        except Exception as e:
            logger.error(f"{agent_name} failed after retries: {e}")
            failed_agents.append(agent_name)
            fallback_data["error"] = str(e)
            return fallback_data
    
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
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
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
