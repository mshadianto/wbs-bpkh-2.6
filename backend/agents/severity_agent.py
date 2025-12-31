"""
WBS BPKH AI - Severity Agent
============================
Assesses severity level and risk of violations.
"""

from groq import Groq
from typing import Dict, Any
import json
from loguru import logger


class SeverityAgent:
    """
    Severity Agent - Assesses risk level
    
    Severity Levels:
    - LOW: Minor violation, limited impact
    - MEDIUM: Moderate violation, potential financial loss
    - HIGH: Serious violation, significant impact
    - CRITICAL: Very serious, involves senior officials or major loss
    """
    
    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "SeverityAgent"
    
    async def assess(
        self,
        report_content: str,
        intake_result: Dict[str, Any],
        fraud_result: Dict[str, Any],
        compliance_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess severity level based on all inputs"""
        
        system_prompt = """Anda adalah Severity Assessment Agent untuk Whistleblowing System.
Tugas Anda adalah menentukan tingkat keparahan (severity) laporan pelanggaran.

KRITERIA PENILAIAN:

1. DAMPAK FINANSIAL
   - < Rp 10 juta: Minor
   - Rp 10 - 100 juta: Moderate
   - Rp 100 juta - 1 milyar: Significant
   - > Rp 1 milyar: Severe

2. LEVEL KETERLIBATAN
   - Staf: +0 poin
   - Supervisor/Manager: +1 poin
   - Direktur/Kepala Bidang: +2 poin
   - Pimpinan/Badan Pelaksana: +3 poin

3. DAMPAK REPUTASI
   - Internal saja: Low
   - Potensi media lokal: Medium
   - Potensi media nasional: High
   - Potensi media internasional: Critical

4. BUKTI TERSEDIA
   - Tidak ada: Low
   - Bukti tidak langsung: Medium
   - Bukti langsung parsial: High
   - Bukti lengkap: Very High

5. FRAUD SCORE
   - < 0.3: Low indicator
   - 0.3 - 0.7: Medium indicator
   - > 0.7: High indicator

SEVERITY MATRIX:
- LOW: Dampak terbatas, tidak melibatkan pejabat senior, fraud score < 0.3
- MEDIUM: Dampak moderat, atau melibatkan manager, fraud score 0.3-0.5
- HIGH: Dampak signifikan, melibatkan direktur, fraud score 0.5-0.7
- CRITICAL: Dampak besar, melibatkan pimpinan, fraud score > 0.7, atau kerugian > 1M

Output dalam format JSON:
{
    "level": "LOW|MEDIUM|HIGH|CRITICAL",
    "score": 0-100,
    "factors": {
        "financial_impact": {
            "assessment": "MINOR|MODERATE|SIGNIFICANT|SEVERE",
            "score": 0-25,
            "notes": "catatan"
        },
        "involvement_level": {
            "assessment": "STAFF|MANAGER|DIRECTOR|EXECUTIVE",
            "score": 0-25,
            "notes": "catatan"
        },
        "reputation_risk": {
            "assessment": "LOW|MEDIUM|HIGH|CRITICAL",
            "score": 0-25,
            "notes": "catatan"
        },
        "evidence_strength": {
            "assessment": "WEAK|MODERATE|STRONG|VERY_STRONG",
            "score": 0-25,
            "notes": "catatan"
        }
    },
    "sla": {
        "initial_response_hours": 4-168,
        "review_deadline_days": 1-14,
        "investigation_deadline_days": 7-90
    },
    "escalation_required": true/false,
    "escalation_reason": "alasan eskalasi jika diperlukan",
    "risk_summary": "ringkasan risiko dalam 1-2 kalimat"
}"""

        # Prepare context from previous agents
        context = f"""
HASIL ANALISIS SEBELUMNYA:

1. INTAKE (4W+1H):
- Jenis Pelanggaran: {intake_result.get('what', {}).get('violation_type', 'N/A')}
- Estimasi Kerugian: {intake_result.get('what', {}).get('estimated_loss', 'Tidak disebutkan')}
- Pihak Terlibat: {json.dumps(intake_result.get('who', {}).get('reported_parties', []), ensure_ascii=False)}
- Melibatkan Pejabat Senior: {intake_result.get('who', {}).get('involves_senior_official', False)}
- Kelengkapan Laporan: {intake_result.get('completeness_score', 0):.2f}

2. FRAUD ANALYSIS:
- Fraud Score: {fraud_result.get('fraud_score', 0):.2f}
- Red Flags: {len(fraud_result.get('red_flags_identified', []))} teridentifikasi
- Dampak Finansial: {fraud_result.get('estimated_financial_impact', {}).get('category', 'N/A')}

3. COMPLIANCE:
- Kategori: {json.dumps(compliance_result.get('categories', []), ensure_ascii=False)}
- Potensi Pidana: {compliance_result.get('legal_implications', {}).get('criminal', False)}
- Jumlah Pelanggaran: {len(compliance_result.get('potential_violations', []))}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"LAPORAN ASLI:\n{report_content}\n\n{context}"}
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"
            
            # Ensure valid severity level
            valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            if result.get("level") not in valid_levels:
                result["level"] = "MEDIUM"
            
            # Set default SLA if not provided
            if "sla" not in result:
                result["sla"] = self._get_default_sla(result.get("level", "MEDIUM"))
            
            logger.info(f"{self.name}: Severity = {result['level']}, Score = {result.get('score', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "level": "MEDIUM",
                "score": 50,
                "sla": self._get_default_sla("MEDIUM")
            }
    
    def _get_default_sla(self, level: str) -> Dict[str, int]:
        """Get default SLA based on severity level"""
        sla_matrix = {
            "CRITICAL": {
                "initial_response_hours": 4,
                "review_deadline_days": 1,
                "investigation_deadline_days": 7
            },
            "HIGH": {
                "initial_response_hours": 24,
                "review_deadline_days": 3,
                "investigation_deadline_days": 14
            },
            "MEDIUM": {
                "initial_response_hours": 72,
                "review_deadline_days": 7,
                "investigation_deadline_days": 30
            },
            "LOW": {
                "initial_response_hours": 168,
                "review_deadline_days": 14,
                "investigation_deadline_days": 90
            }
        }
        return sla_matrix.get(level, sla_matrix["MEDIUM"])
