"""
WBS BPKH AI - Knowledge Loader
==============================
Loads regulations and policies into knowledge base.
"""

from typing import Dict, List, Any
from loguru import logger

from .retriever import knowledge_indexer


class KnowledgeLoader:
    """
    Knowledge Loader - Seeds knowledge base with regulations
    
    Includes:
    - Indonesian anti-corruption laws
    - BPKH internal policies
    - ISO 37002 guidelines
    """
    
    # Built-in regulation knowledge
    REGULATIONS = {
        "UU_TIPIKOR": {
            "name": "UU 31/1999 jo UU 20/2001 - Pemberantasan Tindak Pidana Korupsi",
            "content": """
Undang-Undang tentang Pemberantasan Tindak Pidana Korupsi mengatur tentang:

DEFINISI KORUPSI (Pasal 2-3):
Setiap orang yang secara melawan hukum melakukan perbuatan memperkaya diri sendiri atau 
orang lain atau suatu korporasi yang dapat merugikan keuangan negara atau perekonomian negara.
Setiap orang yang dengan tujuan menguntungkan diri sendiri atau orang lain atau suatu korporasi, 
menyalahgunakan kewenangan, kesempatan atau sarana yang ada padanya karena jabatan atau kedudukan.

SUAP (Pasal 5-6):
Memberi atau menjanjikan sesuatu kepada pegawai negeri atau penyelenggara negara dengan maksud 
supaya pegawai negeri atau penyelenggara negara tersebut berbuat atau tidak berbuat sesuatu 
dalam jabatannya.

GRATIFIKASI (Pasal 12B):
Setiap gratifikasi kepada pegawai negeri atau penyelenggara negara dianggap pemberian suap, 
apabila berhubungan dengan jabatannya dan yang berlawanan dengan kewajiban atau tugasnya.
Gratifikasi wajib dilaporkan dalam 30 hari kerja ke KPK.

PEMERASAN (Pasal 12):
Pegawai negeri atau penyelenggara negara yang meminta, menerima, atau memotong pembayaran 
dengan menggunakan kekuasaan jabatannya.

SANKSI:
- Pidana penjara seumur hidup atau minimal 4 tahun maksimal 20 tahun
- Denda minimal Rp 200 juta maksimal Rp 1 miliar
- Pencabutan hak-hak tertentu
- Perampasan harta kekayaan
""",
            "articles": [
                {"number": "2", "content": "Perbuatan memperkaya diri sendiri secara melawan hukum"},
                {"number": "3", "content": "Menyalahgunakan kewenangan karena jabatan"},
                {"number": "5", "content": "Pemberian suap kepada pegawai negeri"},
                {"number": "11", "content": "Pegawai negeri menerima hadiah terkait jabatan"},
                {"number": "12B", "content": "Gratifikasi kepada pegawai negeri"},
                {"number": "12", "content": "Pemerasan oleh pegawai negeri"}
            ]
        },
        
        "PP_DISIPLIN_PNS": {
            "name": "PP 94/2021 - Disiplin Pegawai Negeri Sipil",
            "content": """
Peraturan Pemerintah tentang Disiplin Pegawai Negeri Sipil mengatur:

KEWAJIBAN PNS (Pasal 3):
1. Setia kepada Pancasila dan UUD 1945
2. Menaati peraturan perundang-undangan
3. Melaksanakan tugas dengan jujur, cermat, dan bersemangat
4. Melaporkan jika ada pelanggaran
5. Menjaga kerahasiaan yang menyangkut kebijakan negara
6. Menggunakan barang milik negara secara bertanggung jawab

LARANGAN PNS (Pasal 5):
1. Menyalahgunakan wewenang
2. Menjadi perantara untuk keuntungan pribadi
3. Menerima hadiah yang berhubungan dengan jabatan
4. Bekerja untuk negara lain tanpa izin
5. Memiliki saham yang berhubungan dengan jabatan
6. Melakukan kegiatan yang merugikan negara

TINGKAT HUKUMAN DISIPLIN:
1. Ringan: Teguran lisan, tertulis, pernyataan tidak puas
2. Sedang: Penundaan kenaikan gaji/pangkat, penurunan pangkat
3. Berat: Penurunan pangkat setingkat, pembebasan jabatan, pemberhentian
""",
            "articles": [
                {"number": "3", "content": "Kewajiban Pegawai Negeri Sipil"},
                {"number": "5", "content": "Larangan bagi Pegawai Negeri Sipil"},
                {"number": "7", "content": "Hukuman disiplin ringan"},
                {"number": "8", "content": "Hukuman disiplin sedang"},
                {"number": "9", "content": "Hukuman disiplin berat"}
            ]
        },
        
        "PERPRES_PBJ": {
            "name": "Perpres 16/2018 - Pengadaan Barang/Jasa Pemerintah",
            "content": """
Peraturan Presiden tentang Pengadaan Barang/Jasa Pemerintah mengatur:

PRINSIP PENGADAAN (Pasal 6):
1. Efisien - penggunaan dana dan daya minimal dengan hasil maksimal
2. Efektif - sesuai dengan kebutuhan dan sasaran
3. Transparan - informasi dapat diakses publik
4. Terbuka - dapat diikuti oleh semua penyedia yang memenuhi syarat
5. Bersaing - persaingan sehat antar penyedia
6. Adil - perlakuan sama kepada semua penyedia
7. Akuntabel - dapat dipertanggungjawabkan

ETIKA PENGADAAN (Pasal 7):
1. Melaksanakan tugas secara tertib
2. Bekerja profesional, mandiri, jujur
3. Tidak saling mempengaruhi
4. Menghindari dan mencegah pemborosan
5. Menghindari dan mencegah pertentangan kepentingan

LARANGAN:
1. Menerima hadiah/imbalan terkait pengadaan
2. Diskriminasi terhadap penyedia
3. Pengaturan tender (bid rigging)
4. Konflik kepentingan
5. Kolusi dengan penyedia
""",
            "articles": [
                {"number": "6", "content": "Prinsip pengadaan barang/jasa"},
                {"number": "7", "content": "Etika pengadaan"},
                {"number": "77", "content": "Sanksi daftar hitam"}
            ]
        },
        
        "UU_PDP": {
            "name": "UU 27/2022 - Pelindungan Data Pribadi",
            "content": """
Undang-Undang Pelindungan Data Pribadi mengatur:

DATA PRIBADI:
Data tentang orang perseorangan yang teridentifikasi atau dapat diidentifikasi.

HAK SUBJEK DATA (Pasal 5-13):
1. Hak mendapatkan informasi tentang pemrosesan
2. Hak mengakses data pribadi
3. Hak memperbaiki data yang tidak akurat
4. Hak menghapus data pribadi
5. Hak menarik persetujuan
6. Hak mengajukan keberatan
7. Hak mendapatkan ganti rugi

KEWAJIBAN PENGENDALI DATA (Pasal 16-27):
1. Memiliki dasar pemrosesan data
2. Menjaga keamanan data
3. Melakukan penilaian dampak
4. Memberitahu jika terjadi kebocoran
5. Menunjuk petugas pelindungan data

SANKSI (Pasal 57-76):
1. Administratif: Peringatan, penghentian, penghapusan, denda
2. Pidana: Penjara maksimal 6 tahun, denda maksimal Rp 6 miliar
""",
            "articles": [
                {"number": "16", "content": "Dasar pemrosesan data pribadi"},
                {"number": "34", "content": "Larangan pengungkapan data pribadi"},
                {"number": "46", "content": "Sanksi administratif"},
                {"number": "67", "content": "Sanksi pidana kebocoran data"}
            ]
        },
        
        "ISO_37002": {
            "name": "ISO 37002:2021 - Whistleblowing Management Systems",
            "content": """
ISO 37002 adalah standar internasional untuk sistem manajemen whistleblowing.

PRINSIP UTAMA:
1. Kepercayaan - membangun lingkungan yang mendukung pelaporan
2. Ketidakberpihakan - penanganan objektif dan adil
3. Perlindungan - melindungi pelapor dari pembalasan

ELEMEN SISTEM (Pasal 4-10):
1. Konteks Organisasi - memahami kebutuhan dan harapan
2. Kepemimpinan - komitmen dan kebijakan
3. Perencanaan - risiko dan tujuan
4. Dukungan - sumber daya dan kompetensi
5. Operasi - proses penerimaan dan penanganan
6. Evaluasi Kinerja - pemantauan dan tinjauan
7. Perbaikan - tindakan korektif

PROSES PENANGANAN:
1. Penerimaan laporan (Receiving)
2. Penilaian awal (Assessing)
3. Penanganan/investigasi (Addressing)
4. Penutupan kasus (Closing)

PERLINDUNGAN PELAPOR:
1. Kerahasiaan identitas
2. Perlindungan dari pembalasan
3. Dukungan psikologis
4. Hak mendapat informasi perkembangan
5. Komunikasi yang aman

AKUNTABILITAS:
1. Dokumentasi lengkap
2. Audit trail
3. Pelaporan berkala
4. Tinjauan manajemen
""",
            "articles": [
                {"number": "4", "content": "Konteks organisasi dan pihak berkepentingan"},
                {"number": "5", "content": "Kepemimpinan dan komitmen"},
                {"number": "6", "content": "Perencanaan risiko dan peluang"},
                {"number": "7", "content": "Dukungan sumber daya dan kompetensi"},
                {"number": "8", "content": "Operasi sistem whistleblowing"},
                {"number": "9", "content": "Evaluasi kinerja dan pemantauan"},
                {"number": "10", "content": "Perbaikan berkelanjutan"}
            ]
        }
    }
    
    async def load_all(self) -> Dict[str, int]:
        """Load all built-in regulations into knowledge base"""
        results = {}
        
        for key, regulation in self.REGULATIONS.items():
            try:
                count = await knowledge_indexer.index_regulation(
                    regulation_name=regulation["name"],
                    regulation_text=regulation["content"],
                    articles=regulation["articles"]
                )
                results[key] = count
                logger.info(f"Loaded {key}: {count} chunks")
            except Exception as e:
                logger.error(f"Failed to load {key}: {e}")
                results[key] = 0
        
        return results
    
    async def load_custom_document(
        self,
        content: str,
        source: str,
        doc_type: str = "POLICY"
    ) -> int:
        """Load custom document into knowledge base"""
        return await knowledge_indexer.index_document(
            content=content,
            source=source,
            doc_type=doc_type
        )
    
    def get_regulation_summary(self, regulation_key: str) -> str:
        """Get summary of a regulation"""
        if regulation_key in self.REGULATIONS:
            reg = self.REGULATIONS[regulation_key]
            return f"{reg['name']}\n\n{reg['content']}"
        return "Regulation not found"
    
    def list_available_regulations(self) -> List[str]:
        """List all available built-in regulations"""
        return list(self.REGULATIONS.keys())


# Export instance
knowledge_loader = KnowledgeLoader()
