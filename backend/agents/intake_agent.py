"""
WBS BPKH AI - Intake Agent
==========================
Parses whistleblower reports using 4W+1H framework.
(What, Who, When, Where, How)
"""

from groq import Groq
from typing import Dict, Any
import asyncio
import json
from loguru import logger


class IntakeAgent:
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
        self.client = client
        self.model = model
        self.name = "IntakeAgent"
    
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

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Laporan Pelanggaran:\n\n{report_content}"}
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"
            
            # Calculate completeness score if not provided
            if "completeness_score" not in result or result["completeness_score"] == 0:
                result["completeness_score"] = self._calculate_completeness(result)
            
            logger.info(f"{self.name}: Parsed report with completeness={result['completeness_score']:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
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
