"""
WBS BPKH AI - Audit & Bias Detection Agent
===========================================
Cross-validates consistency between agents and
detects potential biases in the analysis pipeline.
"""

from groq import Groq
from typing import Dict, Any
import asyncio
import json
from loguru import logger


class AuditAgent:
    """
    Audit & Bias Detection Agent

    Performs cross-validation between agent outputs to ensure
    consistency and detects potential cultural, severity, or
    confirmation biases in the analysis.
    """

    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "AuditAgent"

    async def audit(
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
        Audit analysis results for consistency and bias.

        Args:
            report_content: Original report text
            intake_result: IntakeAgent output
            fraud_result: AnalysisAgent output
            compliance_result: ComplianceAgent output
            severity_result: SeverityAgent output
            recommendation_result: RecommendationAgent output
            summary_result: SummaryAgent output

        Returns:
            Audit result with consistency scores, bias detection, and flags
        """

        system_prompt = """Anda adalah Audit & Bias Detection Agent untuk Whistleblowing System BPKH.
Tugas Anda adalah melakukan cross-validation antar hasil analisis agent dan mendeteksi potensi bias.

PROSES AUDIT:

1. KONSISTENSI ANTAR-AGENT
   a. Fraud Score vs Severity Level:
      - fraud_score 0.0-0.30 seharusnya → severity LOW/MEDIUM
      - fraud_score 0.31-0.70 seharusnya → severity MEDIUM/HIGH
      - fraud_score 0.71-1.00 seharusnya → severity HIGH/CRITICAL
      - Flag jika ada ketidaksesuaian signifikan

   b. Compliance Categories vs Intake Findings:
      - Kategori pelanggaran harus konsisten dengan jenis pelanggaran di intake
      - Flag jika compliance menyebutkan kategori yang tidak relevan dengan intake

   c. Severity vs Recommendations:
      - Severity CRITICAL harus memiliki rekomendasi ESCALATE/INVESTIGATE
      - Severity LOW tidak seharusnya merekomendasikan tindakan darurat
      - Rekomendasi harus proporsional dengan severity

   d. Executive Summary vs Detail Findings:
      - Key findings harus mencerminkan temuan dari agent lain
      - Risk assessment harus konsisten dengan severity level

2. DETEKSI BIAS
   a. Bias Budaya/Nama:
      - Apakah severity dipengaruhi oleh nama/jabatan yang terdengar tertentu?
      - Apakah analisis berubah karena faktor non-relevan?

   b. Severity Inflation:
      - Apakah severity dinaikkan tanpa bukti memadai?
      - Apakah fraud score terlalu tinggi dibanding bukti yang ada?

   c. Severity Deflation:
      - Apakah kasus serius diremehkan?
      - Apakah ada tanda-tanda minimisasi pelanggaran?

   d. Proportionality:
      - Apakah rekomendasi proporsional dengan temuan?
      - Apakah tindakan yang disarankan sesuai dengan severity?

   e. Confirmation Bias:
      - Apakah analisis hanya mencari bukti yang mendukung satu kesimpulan?
      - Apakah ada perspektif alternatif yang diabaikan?

3. KONSISTENSI INTERNAL
   - Apakah informasi yang sama dilaporkan secara konsisten di seluruh agent?
   - Apakah ada kontradiksi antar output agent?

Output dalam format JSON:
{
    "consistency_score": 0.0-1.0,
    "bias_risk": {
        "level": "LOW|MEDIUM|HIGH",
        "types_detected": ["jenis bias yang terdeteksi"],
        "details": "penjelasan detail bias yang ditemukan"
    },
    "cross_validation": {
        "fraud_vs_severity": {
            "consistent": true/false,
            "fraud_score": 0.0,
            "severity_level": "LEVEL",
            "expected_severity_range": ["LEVEL1", "LEVEL2"],
            "notes": "catatan"
        },
        "compliance_vs_intake": {
            "consistent": true/false,
            "mismatched_categories": ["kategori yang tidak cocok"],
            "notes": "catatan"
        },
        "severity_vs_recommendations": {
            "consistent": true/false,
            "proportional": true/false,
            "notes": "catatan"
        },
        "summary_vs_findings": {
            "consistent": true/false,
            "missing_in_summary": ["temuan penting yang tidak ada di summary"],
            "notes": "catatan"
        }
    },
    "audit_flags": [
        {
            "flag_type": "INCONSISTENCY|BIAS|PROPORTIONALITY|MISSING_DATA",
            "severity": "HIGH|MEDIUM|LOW",
            "description": "deskripsi masalah",
            "affected_agents": ["nama agent yang terpengaruh"],
            "recommendation": "saran perbaikan"
        }
    ],
    "corrections": [
        {
            "agent": "nama agent",
            "field": "field yang perlu dikoreksi",
            "current_value": "nilai saat ini",
            "suggested_value": "nilai yang disarankan",
            "reason": "alasan koreksi"
        }
    ],
    "overall_assessment": "CONSISTENT|MINOR_ISSUES|MAJOR_ISSUES|UNRELIABLE",
    "audit_summary": "ringkasan audit dalam 2-3 kalimat",
    "confidence_in_analysis": "HIGH|MEDIUM|LOW"
}

PENTING:
- Bersikap objektif dan tidak memihak
- Fokus pada fakta dan logika, bukan asumsi
- Setiap flag harus didukung oleh bukti spesifik dari output agent
- Berikan saran perbaikan yang konstruktif
- Jangan menambahkan analisis baru, hanya audit hasil yang ada"""

        # Build structured user prompt with key metrics highlighted
        fraud_score = fraud_result.get("fraud_score", 0)
        severity_level = severity_result.get("level", "N/A")
        categories = compliance_result.get("categories", [])
        overall_rec = recommendation_result.get("overall_recommendation", "N/A")

        user_prompt = f"""LAPORAN ASLI:
{report_content}

{'=' * 50}
HASIL ANALISIS UNTUK DI-AUDIT:
{'=' * 50}

METRIK UTAMA:
- Fraud Score: {fraud_score}
- Severity Level: {severity_level}
- Kategori Compliance: {json.dumps(categories, ensure_ascii=False)}
- Overall Recommendation: {overall_rec}

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

Lakukan audit menyeluruh terhadap konsistensi dan potensi bias dari seluruh hasil analisis di atas."""

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
                f"{self.name}: Consistency={result['consistency_score']:.2f}, "
                f"Bias={result['bias_risk']['level']}, "
                f"Assessment={result['overall_assessment']}"
            )
            return result

        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "consistency_score": 0.5,
                "bias_risk": {
                    "level": "LOW",
                    "types_detected": [],
                    "details": "Error during audit"
                },
                "cross_validation": {},
                "audit_flags": [],
                "corrections": [],
                "overall_assessment": "MINOR_ISSUES",
                "audit_summary": "Error during audit process",
                "confidence_in_analysis": "LOW"
            }

    def _validate_result(self, result: dict) -> dict:
        """Post-processing validation of audit result"""
        # Ensure consistency_score is within bounds
        result["consistency_score"] = max(0.0, min(1.0, result.get("consistency_score", 0.5)))

        # Ensure bias_risk has required fields
        if not isinstance(result.get("bias_risk"), dict):
            result["bias_risk"] = {
                "level": "LOW",
                "types_detected": [],
                "details": "Tidak terdeteksi bias signifikan"
            }

        # Validate bias_risk level
        valid_bias_levels = ["LOW", "MEDIUM", "HIGH"]
        if result["bias_risk"].get("level") not in valid_bias_levels:
            result["bias_risk"]["level"] = "MEDIUM"

        # Ensure lists
        if not isinstance(result.get("audit_flags"), list):
            result["audit_flags"] = []
        if not isinstance(result.get("corrections"), list):
            result["corrections"] = []

        # Validate overall_assessment
        valid_assessments = ["CONSISTENT", "MINOR_ISSUES", "MAJOR_ISSUES", "UNRELIABLE"]
        if result.get("overall_assessment") not in valid_assessments:
            result["overall_assessment"] = "MINOR_ISSUES"

        # Validate confidence_in_analysis
        valid_confidence = ["HIGH", "MEDIUM", "LOW"]
        if result.get("confidence_in_analysis") not in valid_confidence:
            result["confidence_in_analysis"] = "MEDIUM"

        return result

    def _truncate_json(self, data: dict, max_chars: int = 3000) -> str:
        """Truncate JSON output to prevent token overflow"""
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if len(text) > max_chars:
            return text[:max_chars] + "\n... [dipotong]"
        return text
