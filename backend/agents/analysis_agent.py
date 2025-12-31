"""
WBS BPKH AI - Analysis Agent
============================
Analyzes fraud indicators and calculates fraud score.
"""

from groq import Groq
from typing import Dict, Any
import json
from loguru import logger


class AnalysisAgent:
    """
    Analysis Agent - Evaluates fraud indicators
    
    Analyzes:
    - Red flags and warning signs
    - Pattern recognition
    - Financial impact indicators
    - Fraud triangle elements (Pressure, Opportunity, Rationalization)
    """
    
    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "AnalysisAgent"
    
    async def analyze(
        self,
        report_content: str,
        intake_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze fraud indicators from report"""
        
        system_prompt = """Anda adalah Fraud Analysis Agent untuk Whistleblowing System.
Tugas Anda adalah menganalisis indikator fraud/kecurangan dari laporan.

Gunakan framework analisis:
1. RED FLAGS - tanda-tanda peringatan
2. FRAUD TRIANGLE - Pressure, Opportunity, Rationalization
3. PATTERN ANALYSIS - pola pelanggaran

Output dalam format JSON:
{
    "fraud_score": 0.0-1.0,
    "score_breakdown": {
        "red_flags_score": 0.0-1.0,
        "evidence_strength": 0.0-1.0,
        "financial_impact": 0.0-1.0,
        "pattern_match": 0.0-1.0
    },
    "red_flags_identified": [
        {
            "flag": "deskripsi red flag",
            "severity": "HIGH|MEDIUM|LOW",
            "indicator_type": "jenis indikator"
        }
    ],
    "fraud_triangle": {
        "pressure": {
            "identified": true/false,
            "description": "tekanan yang mendorong"
        },
        "opportunity": {
            "identified": true/false,
            "description": "kesempatan yang ada"
        },
        "rationalization": {
            "identified": true/false,
            "description": "pembenaran yang mungkin"
        }
    },
    "estimated_financial_impact": {
        "category": "NEGLIGIBLE|MINOR|MODERATE|SIGNIFICANT|SEVERE",
        "estimated_range": "range estimasi kerugian",
        "basis": "dasar estimasi"
    },
    "similar_patterns": ["pola serupa yang teridentifikasi"],
    "confidence_level": "HIGH|MEDIUM|LOW",
    "analysis_notes": "catatan analisis tambahan"
}

FRAUD SCORE INTERPRETATION:
- 0.00 - 0.30: Indikasi RENDAH (belum cukup bukti)
- 0.31 - 0.70: Indikasi SEDANG (perlu investigasi)
- 0.71 - 1.00: Indikasi TINGGI (prioritas tinggi)"""

        # Prepare context from intake
        intake_context = f"""
HASIL PARSING 4W+1H:
- What: {json.dumps(intake_result.get('what', {}), ensure_ascii=False)}
- Who: {json.dumps(intake_result.get('who', {}), ensure_ascii=False)}
- When: {json.dumps(intake_result.get('when', {}), ensure_ascii=False)}
- Where: {json.dumps(intake_result.get('where', {}), ensure_ascii=False)}
- How: {json.dumps(intake_result.get('how', {}), ensure_ascii=False)}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"LAPORAN ASLI:\n{report_content}\n\n{intake_context}"}
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"
            
            # Ensure fraud_score is within bounds
            result["fraud_score"] = max(0.0, min(1.0, result.get("fraud_score", 0.5)))
            
            logger.info(f"{self.name}: Fraud score = {result['fraud_score']:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "fraud_score": 0.5,
                "red_flags_identified": [],
                "confidence_level": "LOW"
            }
    
    def interpret_score(self, score: float) -> Dict[str, str]:
        """Interpret fraud score"""
        if score <= 0.30:
            return {
                "level": "LOW",
                "interpretation": "Indikasi rendah - bukti belum mencukupi",
                "action": "Monitor dan kumpulkan informasi tambahan"
            }
        elif score <= 0.70:
            return {
                "level": "MEDIUM",
                "interpretation": "Indikasi sedang - perlu investigasi lebih lanjut",
                "action": "Lakukan telaah mendalam dan klarifikasi"
            }
        else:
            return {
                "level": "HIGH",
                "interpretation": "Indikasi tinggi - bukti kuat dugaan pelanggaran",
                "action": "Prioritaskan untuk investigasi segera"
            }
