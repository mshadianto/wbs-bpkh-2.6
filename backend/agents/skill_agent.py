"""
WBS BPKH AI - Skill Verification Agent
=======================================
Verifies that all agent outputs are factually grounded
in the original report text. Detects hallucinations.
"""

from groq import Groq
from typing import Dict, Any
import asyncio
import json
from loguru import logger


class SkillAgent:
    """
    Skill Verification Agent - Anti-Hallucination Check

    Compares every claim made by prior agents against the original
    report text to detect fabricated or unsupported information.
    """

    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "SkillAgent"

    async def verify(
        self,
        report_content: str,
        intake_result: Dict[str, Any],
        fraud_result: Dict[str, Any],
        compliance_result: Dict[str, Any],
        severity_result: Dict[str, Any],
        recommendation_result: Dict[str, Any],
        summary_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify grounding of all agent outputs against original report.

        Args:
            report_content: Original report text
            intake_result: IntakeAgent output
            fraud_result: AnalysisAgent output
            compliance_result: ComplianceAgent output
            severity_result: SeverityAgent output
            recommendation_result: RecommendationAgent output
            summary_result: SummaryAgent output

        Returns:
            Verification result with grounding scores and hallucination flags
        """

        system_prompt = """Anda adalah Skill Verification Agent untuk Whistleblowing System BPKH.
Tugas Anda adalah memverifikasi bahwa seluruh output analisis AI BENAR-BENAR berdasarkan informasi yang ada dalam laporan asli. Anda harus mendeteksi hallucination (informasi yang dibuat-buat/tidak ada dalam laporan).

PROSES VERIFIKASI:

1. INTAKE VERIFICATION
   - Apakah semua klaim dalam parsing 4W+1H benar-benar ada dalam teks laporan?
   - Apakah ada informasi yang ditambahkan yang tidak disebutkan pelapor?

2. FRAUD ANALYSIS VERIFICATION
   - Apakah red flags yang teridentifikasi didukung oleh bukti dari laporan?
   - Apakah fraud triangle elements benar-benar tersirat dalam laporan?
   - Apakah estimasi dampak finansial berdasarkan data dari laporan?

3. COMPLIANCE VERIFICATION
   - Apakah pelanggaran regulasi yang disebutkan relevan dengan isi laporan?
   - Apakah ada pasal/regulasi yang dikaitkan tanpa dasar dari laporan?

4. SEVERITY VERIFICATION
   - Apakah faktor-faktor severity didukung oleh fakta dalam laporan?
   - Apakah level keterlibatan pejabat sesuai dengan yang disebutkan?

5. RECOMMENDATION VERIFICATION
   - Apakah rekomendasi proporsional dengan temuan yang terbukti?

SCORING:
- grounding_score 1.0: Semua klaim 100% berdasarkan laporan
- grounding_score 0.7-0.99: Sebagian besar akurat, sedikit asumsi
- grounding_score 0.4-0.69: Banyak asumsi yang tidak didukung laporan
- grounding_score 0.0-0.39: Banyak hallucination terdeteksi

Output dalam format JSON:
{
    "grounding_score": 0.0-1.0,
    "agent_verification": {
        "intake": {
            "grounded": true/false,
            "score": 0.0-1.0,
            "hallucinations": ["klaim yang tidak ada dalam laporan"],
            "unsupported_claims": ["klaim yang tidak cukup didukung"],
            "notes": "catatan verifikasi"
        },
        "fraud_analysis": {
            "grounded": true/false,
            "score": 0.0-1.0,
            "hallucinations": ["indikator fraud yang dibuat-buat"],
            "unsupported_claims": ["klaim tanpa bukti memadai"],
            "notes": "catatan verifikasi"
        },
        "compliance": {
            "grounded": true/false,
            "score": 0.0-1.0,
            "hallucinations": ["regulasi yang tidak relevan dikaitkan"],
            "unsupported_claims": ["pasal tanpa dasar dari laporan"],
            "notes": "catatan verifikasi"
        },
        "severity": {
            "grounded": true/false,
            "score": 0.0-1.0,
            "hallucinations": ["faktor severity yang dibuat-buat"],
            "unsupported_claims": [],
            "notes": "catatan verifikasi"
        },
        "recommendations": {
            "grounded": true/false,
            "score": 0.0-1.0,
            "hallucinations": [],
            "unsupported_claims": ["rekomendasi tanpa dasar temuan"],
            "notes": "catatan verifikasi"
        }
    },
    "total_hallucinations": 0,
    "total_unsupported_claims": 0,
    "confidence_threshold_met": true/false,
    "verification_summary": "ringkasan hasil verifikasi dalam 2-3 kalimat",
    "recommended_action": "ACCEPT|REVIEW|REANALYZE"
}

PENTING:
- Bandingkan SETIAP klaim dengan teks laporan asli
- Jika informasi tidak ada dalam laporan tetapi muncul dalam analisis, itu adalah hallucination
- Jika informasi ada tapi ditafsirkan berlebihan, itu unsupported_claim
- Bersikap ketat dan kritis dalam verifikasi
- Jangan menambahkan informasi baru, hanya verifikasi"""

        user_prompt = f"""LAPORAN ASLI:
{report_content}

{'=' * 50}
HASIL ANALISIS YANG PERLU DIVERIFIKASI:
{'=' * 50}

1. INTAKE (4W+1H):
{self._truncate_json(intake_result)}

2. FRAUD ANALYSIS:
{self._truncate_json(fraud_result)}

3. COMPLIANCE:
{self._truncate_json(compliance_result)}

4. SEVERITY:
{self._truncate_json(severity_result)}

5. RECOMMENDATIONS:
{self._truncate_json(recommendation_result)}

6. EXECUTIVE SUMMARY:
{self._truncate_json(summary_result)}

Verifikasi setiap klaim terhadap LAPORAN ASLI di atas. Identifikasi hallucination dan klaim yang tidak didukung."""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=3072,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"

            # Post-processing validation
            result = self._validate_result(result)

            logger.info(
                f"{self.name}: Grounding score={result['grounding_score']:.2f}, "
                f"Hallucinations={result['total_hallucinations']}, "
                f"Action={result['recommended_action']}"
            )
            return result

        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "grounding_score": 0.5,
                "agent_verification": {},
                "total_hallucinations": 0,
                "total_unsupported_claims": 0,
                "confidence_threshold_met": False,
                "verification_summary": "Error during verification",
                "recommended_action": "REVIEW"
            }

    def _validate_result(self, result: dict) -> dict:
        """Post-processing validation of verification result"""
        # Ensure grounding_score is within bounds
        result["grounding_score"] = max(0.0, min(1.0, result.get("grounding_score", 0.5)))

        # Count total hallucinations and unsupported claims across all agents
        total_h = 0
        total_u = 0
        agent_keys = ["intake", "fraud_analysis", "compliance", "severity", "recommendations"]
        for key in agent_keys:
            agent_check = result.get("agent_verification", {}).get(key, {})
            total_h += len(agent_check.get("hallucinations", []))
            total_u += len(agent_check.get("unsupported_claims", []))
        result["total_hallucinations"] = total_h
        result["total_unsupported_claims"] = total_u

        # Set confidence threshold (grounding_score >= 0.7 passes)
        result["confidence_threshold_met"] = result["grounding_score"] >= 0.7

        # Determine recommended action based on grounding score
        if result["grounding_score"] >= 0.8:
            result["recommended_action"] = "ACCEPT"
        elif result["grounding_score"] >= 0.5:
            result["recommended_action"] = "REVIEW"
        else:
            result["recommended_action"] = "REANALYZE"

        return result

    def _truncate_json(self, data: dict, max_chars: int = 3000) -> str:
        """Truncate JSON output to prevent token overflow"""
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if len(text) > max_chars:
            return text[:max_chars] + "\n... [dipotong]"
        return text
