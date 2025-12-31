"""
WBS BPKH AI - Compliance Agent
==============================
Checks violations against regulations and policies.
Uses RAG for regulation knowledge base.
"""

from groq import Groq
from typing import Dict, Any, Optional
import json
from loguru import logger


class ComplianceAgent:
    """
    Compliance Agent - Checks regulatory violations
    
    References:
    - UU 31/1999 & UU 20/2001 (Tipikor)
    - UU 28/1999 (Penyelenggaraan Negara Bersih KKN)
    - UU 27/2022 (Perlindungan Data Pribadi)
    - PP 94/2021 (Disiplin PNS)
    - Perpres 16/2018 (Pengadaan Barang/Jasa)
    - Kode Etik BPKH
    - SOP Internal BPKH
    """
    
    REGULATION_KNOWLEDGE = """
REGULASI UTAMA:

1. UU 31/1999 jo UU 20/2001 (Pemberantasan Tindak Pidana Korupsi)
   - Pasal 2: Perbuatan memperkaya diri sendiri/orang lain/korporasi
   - Pasal 3: Menyalahgunakan kewenangan untuk menguntungkan diri
   - Pasal 5: Suap kepada penyelenggara negara
   - Pasal 11: Pegawai negeri menerima hadiah
   - Pasal 12B: Gratifikasi

2. UU 28/1999 (Penyelenggaraan Negara Bebas KKN)
   - Asas kepastian hukum, tertib penyelenggaraan negara
   - Asas kepentingan umum, keterbukaan, proporsionalitas
   - Kewajiban melaporkan harta kekayaan

3. UU 27/2022 (Perlindungan Data Pribadi)
   - Pasal 16: Pemrosesan data pribadi
   - Pasal 34: Larangan pengungkapan data pribadi
   - Pasal 46-49: Sanksi administratif dan pidana

4. PP 94/2021 (Disiplin Pegawai Negeri Sipil)
   - Pasal 3: Kewajiban PNS
   - Pasal 5: Larangan PNS
   - Pasal 7-9: Jenis dan tingkat hukuman disiplin

5. Perpres 16/2018 (Pengadaan Barang/Jasa Pemerintah)
   - Pasal 6: Prinsip pengadaan
   - Pasal 7: Etika pengadaan
   - Larangan KKN dan conflict of interest

6. Perka LKPP tentang Benturan Kepentingan
   - Definisi dan jenis benturan kepentingan
   - Kewajiban pelaporan dan penanganan

7. Kode Etik BPKH
   - Integritas dan profesionalisme
   - Kepatuhan terhadap aturan
   - Tanggung jawab pengelolaan dana haji
"""
    
    def __init__(self, client: Groq, model: str):
        self.client = client
        self.model = model
        self.name = "ComplianceAgent"
    
    async def check(
        self,
        report_content: str,
        intake_result: Dict[str, Any],
        rag_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check compliance violations"""
        
        # Combine built-in knowledge with RAG context
        knowledge_base = self.REGULATION_KNOWLEDGE
        if rag_context:
            knowledge_base += f"\n\nKONTEKS TAMBAHAN DARI RAG:\n{rag_context}"
        
        system_prompt = f"""Anda adalah Compliance Agent untuk Whistleblowing System BPKH.
Tugas Anda adalah mengidentifikasi regulasi dan kebijakan yang berpotensi dilanggar.

{knowledge_base}

Analisis laporan dan berikan output dalam format JSON:
{{
    "categories": ["FRAUD", "CORRUPTION", "GRATIFICATION", "COI", "PROCUREMENT", "DATA_BREACH", "ETHICS", "MISCONDUCT", "OTHER"],
    "potential_violations": [
        {{
            "regulation": "nama regulasi",
            "article": "pasal yang dilanggar",
            "description": "deskripsi pelanggaran",
            "severity": "HIGH|MEDIUM|LOW",
            "evidence_in_report": "bukti dari laporan"
        }}
    ],
    "compliance_status": {{
        "uu_tipikor": {{
            "applicable": true/false,
            "articles": ["pasal relevan"],
            "notes": "catatan"
        }},
        "uu_pdp": {{
            "applicable": true/false,
            "articles": ["pasal relevan"],
            "notes": "catatan"
        }},
        "pp_disiplin": {{
            "applicable": true/false,
            "articles": ["pasal relevan"],
            "notes": "catatan"
        }},
        "perpres_pbj": {{
            "applicable": true/false,
            "articles": ["pasal relevan"],
            "notes": "catatan"
        }},
        "kode_etik_bpkh": {{
            "applicable": true/false,
            "provisions": ["ketentuan relevan"],
            "notes": "catatan"
        }}
    }},
    "legal_implications": {{
        "criminal": true/false,
        "administrative": true/false,
        "civil": true/false,
        "notes": "implikasi hukum"
    }},
    "recommended_references": ["referensi regulasi untuk investigasi"],
    "confidence_level": "HIGH|MEDIUM|LOW"
}}"""

        # Prepare context from intake
        intake_context = f"""
HASIL PARSING LAPORAN:
- Jenis Pelanggaran: {intake_result.get('what', {}).get('violation_type', 'N/A')}
- Pihak Terlibat: {json.dumps(intake_result.get('who', {}).get('reported_parties', []), ensure_ascii=False)}
- Modus: {intake_result.get('how', {}).get('modus_operandi', 'N/A')}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"LAPORAN:\n{report_content}\n\n{intake_context}"}
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["agent"] = self.name
            result["status"] = "SUCCESS"
            
            # Ensure categories is a list
            if not isinstance(result.get("categories"), list):
                result["categories"] = ["OTHER"]
            
            logger.info(f"{self.name}: Found {len(result.get('potential_violations', []))} potential violations")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "agent": self.name,
                "status": "ERROR",
                "error": str(e),
                "categories": ["OTHER"],
                "potential_violations": [],
                "confidence_level": "LOW"
            }
