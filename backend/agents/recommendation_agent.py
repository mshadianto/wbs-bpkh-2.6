"""
WBS BPKH AI - Recommendation Agent
==================================
Generates recommended actions based on analysis.
"""

from groq import Groq
from typing import Dict, Any, Optional, List
import json
from loguru import logger


class RecommendationAgent:
    """
    Recommendation Agent - Generates action recommendations
    
    Recommendations based on:
    - Severity level
    - Fraud score
    - Compliance issues
    - Similar historical cases
    """
    
    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "RecommendationAgent"
    
    async def recommend(
        self,
        report_content: str,
        intake_result: Dict[str, Any],
        fraud_result: Dict[str, Any],
        compliance_result: Dict[str, Any],
        severity_result: Dict[str, Any],
        similar_cases: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate recommendations based on all analysis"""
        
        system_prompt = """Anda adalah Recommendation Agent untuk Whistleblowing System BPKH.
Tugas Anda adalah memberikan rekomendasi tindakan berdasarkan hasil analisis.

JENIS REKOMENDASI:

1. IMMEDIATE ACTIONS (dalam 24 jam)
   - Eskalasi ke pimpinan
   - Pengamanan bukti
   - Penghentian sementara proses terkait
   - Notifikasi ke pihak terkait

2. SHORT-TERM ACTIONS (1-7 hari)
   - Klarifikasi tambahan ke pelapor
   - Pengumpulan data awal
   - Koordinasi dengan unit terkait
   - Analisis dokumen pendukung

3. INVESTIGATION ACTIONS (sesuai SLA)
   - Audit investigatif
   - Wawancara saksi
   - Pemeriksaan dokumen
   - Analisis forensik (jika perlu)

4. FOLLOW-UP ACTIONS
   - Pelaporan ke pelapor
   - Dokumentasi hasil
   - Tindakan perbaikan
   - Monitoring

Output dalam format JSON:
{
    "immediate_actions": [
        {
            "action": "deskripsi tindakan",
            "priority": "P1|P2|P3",
            "responsible_party": "pihak pelaksana",
            "deadline": "deadline",
            "rationale": "alasan"
        }
    ],
    "short_term_actions": [
        {
            "action": "deskripsi tindakan",
            "priority": "P1|P2|P3",
            "responsible_party": "pihak pelaksana",
            "deadline": "deadline"
        }
    ],
    "investigation_requirements": {
        "type": "PRELIMINARY|STANDARD|COMPREHENSIVE",
        "scope": ["area yang perlu diinvestigasi"],
        "resources_needed": ["sumber daya yang diperlukan"],
        "estimated_duration": "estimasi durasi"
    },
    "stakeholder_notifications": [
        {
            "stakeholder": "pihak yang perlu diberitahu",
            "timing": "kapan",
            "content_type": "jenis informasi"
        }
    ],
    "risk_mitigation": [
        {
            "risk": "risiko yang dimitigasi",
            "mitigation_action": "tindakan mitigasi",
            "priority": "HIGH|MEDIUM|LOW"
        }
    ],
    "follow_up_schedule": {
        "first_review": "waktu review pertama",
        "progress_updates": "frekuensi update",
        "closure_timeline": "estimasi penyelesaian"
    },
    "escalation_path": {
        "current_level": "UP1|AUDIT|MANAGEMENT|BOARD",
        "next_escalation_trigger": "kondisi untuk eskalasi berikutnya",
        "final_authority": "otoritas akhir"
    },
    "similar_case_learnings": ["pembelajaran dari kasus serupa"],
    "overall_recommendation": "PROCEED|INVESTIGATE|ESCALATE|HOLD|CLOSE",
    "recommendation_rationale": "alasan rekomendasi"
}"""

        # Prepare context from all previous analyses
        context = f"""
RINGKASAN ANALISIS:

1. SEVERITY: {severity_result.get('level', 'N/A')}
   - Score: {severity_result.get('score', 0)}
   - SLA Response: {severity_result.get('sla', {}).get('initial_response_hours', 72)} jam
   - Eskalasi Diperlukan: {severity_result.get('escalation_required', False)}

2. FRAUD ANALYSIS:
   - Fraud Score: {fraud_result.get('fraud_score', 0):.2f}
   - Confidence: {fraud_result.get('confidence_level', 'N/A')}
   - Red Flags: {len(fraud_result.get('red_flags_identified', []))}

3. COMPLIANCE:
   - Kategori: {json.dumps(compliance_result.get('categories', []), ensure_ascii=False)}
   - Potensi Pelanggaran: {len(compliance_result.get('potential_violations', []))}
   - Implikasi Pidana: {compliance_result.get('legal_implications', {}).get('criminal', False)}

4. INTAKE:
   - Kelengkapan: {intake_result.get('completeness_score', 0):.2f}
   - Elemen Kurang: {json.dumps(intake_result.get('missing_elements', []), ensure_ascii=False)}
"""

        # Add similar cases if available
        if similar_cases:
            context += "\n5. KASUS SERUPA:\n"
            for i, case in enumerate(similar_cases[:3], 1):
                context += f"   - Kasus {i}: {case.get('summary', 'N/A')} (Outcome: {case.get('outcome', 'N/A')})\n"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"LAPORAN:\n{report_content}\n\n{context}"}
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"
            
            logger.info(f"{self.name}: Overall recommendation = {result.get('overall_recommendation', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "overall_recommendation": "INVESTIGATE",
                "immediate_actions": [],
                "short_term_actions": []
            }
