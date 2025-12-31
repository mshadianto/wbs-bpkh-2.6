"""
WBS BPKH AI - Summary Agent
===========================
Generates executive summary from all analysis results.
"""

from groq import Groq
from typing import Dict, Any
import json
from loguru import logger


class SummaryAgent:
    """
    Summary Agent - Creates executive summary
    
    Produces concise, actionable summary for decision makers.
    """
    
    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "SummaryAgent"
    
    async def summarize(
        self,
        report_content: str,
        intake_result: Dict[str, Any],
        fraud_result: Dict[str, Any],
        compliance_result: Dict[str, Any],
        severity_result: Dict[str, Any],
        recommendation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary"""
        
        system_prompt = """Anda adalah Summary Agent untuk Whistleblowing System BPKH.
Tugas Anda adalah membuat Ringkasan Eksekutif yang ringkas dan actionable.

GUIDELINES:
- Tulis dalam Bahasa Indonesia formal
- Maksimal 300 kata
- Fokus pada informasi decision-critical
- Hindari jargon teknis
- Sertakan rekomendasi jelas

Output dalam format JSON:
{
    "title": "Judul Ringkasan Laporan",
    "executive_summary": "Ringkasan dalam 2-3 paragraf yang mencakup: inti laporan, temuan utama, risiko, dan rekomendasi",
    "key_findings": [
        "Temuan kunci 1",
        "Temuan kunci 2",
        "Temuan kunci 3"
    ],
    "risk_assessment": {
        "overall_risk": "LOW|MEDIUM|HIGH|CRITICAL",
        "risk_statement": "Pernyataan risiko dalam 1 kalimat"
    },
    "compliance_summary": "Ringkasan kepatuhan dalam 1-2 kalimat",
    "recommended_action": {
        "primary": "Tindakan utama yang direkomendasikan",
        "timeline": "Timeline pelaksanaan",
        "responsible": "Pihak bertanggung jawab"
    },
    "decision_required": "Keputusan yang diperlukan dari pimpinan",
    "next_steps": [
        "Langkah selanjutnya 1",
        "Langkah selanjutnya 2"
    ],
    "report_metadata": {
        "analysis_confidence": "HIGH|MEDIUM|LOW",
        "data_completeness": "COMPLETE|PARTIAL|MINIMAL",
        "urgency": "IMMEDIATE|URGENT|NORMAL|LOW"
    }
}"""

        # Compile all analysis results
        context = f"""
KOMPILASI HASIL ANALISIS:

═══════════════════════════════════════
SEVERITY: {severity_result.get('level', 'N/A')} (Score: {severity_result.get('score', 0)}/100)
FRAUD SCORE: {fraud_result.get('fraud_score', 0):.2f}
KATEGORI: {', '.join(compliance_result.get('categories', ['N/A']))}
═══════════════════════════════════════

DETAIL 4W+1H:
• What: {intake_result.get('what', {}).get('violation_type', 'N/A')}
  - Deskripsi: {intake_result.get('what', {}).get('description', 'N/A')}
  - Estimasi Kerugian: {intake_result.get('what', {}).get('estimated_loss', 'Tidak disebutkan')}

• Who: {', '.join(intake_result.get('who', {}).get('reported_parties', ['N/A']))}
  - Senior Official: {'Ya' if intake_result.get('who', {}).get('involves_senior_official') else 'Tidak'}

• When: {intake_result.get('when', {}).get('incident_date', 'N/A')}
  - Ongoing: {'Ya' if intake_result.get('when', {}).get('is_ongoing') else 'Tidak'}

• Where: {intake_result.get('where', {}).get('location', 'N/A')}
  - Unit: {intake_result.get('where', {}).get('department', 'N/A')}

• How: {intake_result.get('how', {}).get('modus_operandi', 'N/A')}

RED FLAGS TERIDENTIFIKASI:
{chr(10).join(['• ' + rf.get('flag', '') for rf in fraud_result.get('red_flags_identified', [])[:5]])}

REGULASI BERPOTENSI DILANGGAR:
{chr(10).join(['• ' + pv.get('regulation', '') + ' - ' + pv.get('article', '') for pv in compliance_result.get('potential_violations', [])[:5]])}

IMPLIKASI HUKUM:
• Pidana: {'Ya' if compliance_result.get('legal_implications', {}).get('criminal') else 'Tidak'}
• Administratif: {'Ya' if compliance_result.get('legal_implications', {}).get('administrative') else 'Tidak'}

SLA:
• Response: {severity_result.get('sla', {}).get('initial_response_hours', 72)} jam
• Review: {severity_result.get('sla', {}).get('review_deadline_days', 7)} hari
• Investigation: {severity_result.get('sla', {}).get('investigation_deadline_days', 30)} hari

REKOMENDASI:
• Overall: {recommendation_result.get('overall_recommendation', 'N/A')}
• Rationale: {recommendation_result.get('recommendation_rationale', 'N/A')}

TINDAKAN IMMEDIATE:
{chr(10).join(['• ' + ia.get('action', '') for ia in recommendation_result.get('immediate_actions', [])[:3]])}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"LAPORAN ASLI:\n{report_content}\n\n{context}"}
                ],
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"
            
            logger.info(f"{self.name}: Executive summary generated")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "executive_summary": "Error generating summary",
                "key_findings": [],
                "recommended_action": {"primary": "Manual review required"}
            }
