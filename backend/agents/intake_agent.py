"""
WBS BPKH AI - Intake Agent
==========================
Parses whistleblower reports using 4W+1H framework.
(What, Who, When, Where, How)
"""

from groq import Groq
from typing import Dict, Any
import json
from loguru import logger

from .base_agent import BaseAgent


class IntakeAgent(BaseAgent):
    """
    Intake Agent - Extracts structured information from reports

    Uses 4W+1H framework:
    - What: Apa yang terjadi (pelanggaran)
    - Who: Siapa yang terlibat
    - When: Kapan terjadi
    - Where: Dimana terjadi
    - How: Bagaimana modus operandinya
    """

    def __init__(self, client: Groq, model: str):
        super().__init__(client, model, "IntakeAgent")
    
    async def parse(self, report_content: str) -> Dict[str, Any]:
        """Parse report using 4W+1H framework"""
        
        system_prompt = """Anda adalah Intake Agent untuk Whistleblowing System.
Tugas Anda adalah mengekstrak informasi terstruktur dari laporan pelanggaran menggunakan framework 4W+1H.

PENTING: 
- Ekstrak hanya informasi yang EKSPLISIT disebutkan dalam laporan
- Jika informasi tidak tersedia, isi dengan "Tidak disebutkan"
- Jangan berasumsi atau menambahkan informasi yang tidak ada

Output dalam format JSON:
{
    "what": {
        "violation_type": "jenis pelanggaran yang dilaporkan",
        "description": "deskripsi singkat apa yang terjadi",
        "estimated_loss": "estimasi kerugian jika disebutkan, atau 'Tidak disebutkan'",
        "evidence_mentioned": ["bukti yang disebutkan"]
    },
    "who": {
        "reported_parties": ["nama/jabatan pihak yang dilaporkan"],
        "witnesses": ["saksi jika disebutkan"],
        "affected_parties": ["pihak yang terdampak"],
        "involves_senior_official": true/false
    },
    "when": {
        "incident_date": "tanggal kejadian jika disebutkan",
        "incident_period": "periode kejadian jika berulang",
        "report_date": "tanggal laporan dibuat",
        "is_ongoing": true/false
    },
    "where": {
        "location": "lokasi kejadian",
        "department": "unit/bidang terkait",
        "specific_area": "area spesifik jika disebutkan"
    },
    "how": {
        "modus_operandi": "cara/metode pelanggaran dilakukan",
        "process_violated": "proses/prosedur yang dilanggar",
        "tools_used": ["alat/dokumen yang digunakan"]
    },
    "completeness_score": 0.0-1.0,
    "missing_elements": ["elemen yang tidak lengkap"],
    "clarification_needed": ["pertanyaan klarifikasi yang perlu diajukan"]
}"""

        from .utils import AgentProcessingError

        # LLM call - let API errors propagate for retry_llm_call to handle
        raw = await self._call_llm(
            system_prompt,
            f"Laporan Pelanggaran:\n\n{report_content}",
            max_tokens=2048
        )

        try:
            result = json.loads(raw)
            result["agent"] = self.name
            result["status"] = "SUCCESS"

            # Calculate completeness score if not provided
            if "completeness_score" not in result or result["completeness_score"] == 0:
                result["completeness_score"] = self._calculate_completeness(result)

            logger.info(f"{self.name}: Parsed report with completeness={result['completeness_score']:.2f}")
            return result

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"{self.name} response parsing error: {e}")
            raise AgentProcessingError(
                f"{self.name}: Failed to parse LLM response: {e}",
                fallback_data={
                    "agent": self.name,
                    "status": "ERROR",
                    "error": str(e),
                    "what": {"violation_type": "Error parsing", "description": ""},
                    "who": {"reported_parties": []},
                    "when": {"incident_date": "Unknown"},
                    "where": {"location": "Unknown"},
                    "how": {"modus_operandi": "Unknown"},
                    "completeness_score": 0.0
                }
            )
    
    def _calculate_completeness(self, parsed: Dict[str, Any]) -> float:
        """Calculate completeness score based on parsed elements"""
        score = 0.0
        max_score = 5.0
        
        # Check What
        what = parsed.get("what", {})
        if what.get("violation_type") and what.get("violation_type") != "Tidak disebutkan":
            score += 1.0
        
        # Check Who
        who = parsed.get("who", {})
        if who.get("reported_parties") and len(who.get("reported_parties", [])) > 0:
            if who["reported_parties"][0] != "Tidak disebutkan":
                score += 1.0
        
        # Check When
        when = parsed.get("when", {})
        if when.get("incident_date") and when.get("incident_date") != "Tidak disebutkan":
            score += 1.0
        
        # Check Where
        where = parsed.get("where", {})
        if where.get("location") and where.get("location") != "Tidak disebutkan":
            score += 1.0
        
        # Check How
        how = parsed.get("how", {})
        if how.get("modus_operandi") and how.get("modus_operandi") != "Tidak disebutkan":
            score += 1.0
        
        return score / max_score
