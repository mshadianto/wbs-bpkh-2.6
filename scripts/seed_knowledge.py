#!/usr/bin/env python3
"""
WBS BPKH AI - Knowledge Base Seeder
===================================
Script untuk load regulasi dan dokumen referensi ke dalam RAG system.

Usage:
    python seed_knowledge.py
    python seed_knowledge.py --reset  # Reset dan reload semua
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from supabase import create_client


# ============== Configuration ==============

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing SUPABASE_URL or SUPABASE_KEY in environment")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============== Pre-loaded Regulations ==============

REGULATIONS = {
    "UU_TIPIKOR": {
        "title": "UU 31/1999 jo UU 20/2001 tentang Pemberantasan Tindak Pidana Korupsi",
        "short_name": "UU Tipikor",
        "category": "CORRUPTION",
        "full_text": """
UNDANG-UNDANG REPUBLIK INDONESIA NOMOR 31 TAHUN 1999 TENTANG PEMBERANTASAN TINDAK PIDANA KORUPSI

BAB II - TINDAK PIDANA KORUPSI

Pasal 2:
(1) Setiap orang yang secara melawan hukum melakukan perbuatan memperkaya diri sendiri atau orang lain atau suatu korporasi yang dapat merugikan keuangan negara atau perekonomian negara, dipidana penjara dengan penjara seumur hidup atau pidana penjara paling singkat 4 (empat) tahun dan paling lama 20 (dua puluh) tahun dan denda paling sedikit Rp. 200.000.000,00 (dua ratus juta rupiah) dan paling banyak Rp. 1.000.000.000,00 (satu milyar rupiah).

Pasal 3:
Setiap orang yang dengan tujuan menguntungkan diri sendiri atau orang lain atau suatu korporasi, menyalahgunakan kewenangan, kesempatan atau sarana yang ada padanya karena jabatan atau kedudukan yang dapat merugikan keuangan negara atau perekonomian negara, dipidana dengan pidana penjara seumur hidup atau pidana penjara paling singkat 1 (satu) tahun dan paling lama 20 (dua puluh) tahun dan atau denda paling sedikit Rp. 50.000.000,00 (lima puluh juta rupiah) dan paling banyak Rp. 1.000.000.000,00 (satu milyar rupiah).

Pasal 5:
(1) Dipidana dengan pidana penjara paling singkat 1 (satu) tahun dan paling lama 5 (lima) tahun dan atau pidana denda paling sedikit Rp 50.000.000,00 (lima puluh juta rupiah) dan paling banyak Rp 250.000.000,00 (dua ratus lima puluh juta rupiah) setiap orang yang:
a. memberi atau menjanjikan sesuatu kepada pegawai negeri atau penyelenggara negara dengan maksud supaya pegawai negeri atau penyelenggara negara tersebut berbuat atau tidak berbuat sesuatu dalam jabatannya, yang bertentangan dengan kewajibannya; atau
b. memberi sesuatu kepada pegawai negeri atau penyelenggara negara karena atau berhubungan dengan sesuatu yang bertentangan dengan kewajiban, dilakukan atau tidak dilakukan dalam jabatannya.

Pasal 11:
Dipidana dengan pidana penjara paling singkat 1 (satu) tahun dan paling lama 5 (lima) tahun dan atau pidana denda paling sedikit Rp 50.000.000,00 (lima puluh juta rupiah) dan paling banyak Rp 250.000.000,00 (dua ratus lima puluh juta rupiah) pegawai negeri atau penyelenggara negara yang menerima hadiah atau janji padahal diketahui atau patut diduga, bahwa hadiah atau janji tersebut diberikan karena kekuasaan atau kewenangan yang berhubungan dengan jabatannya, atau yang menurut pikiran orang yang memberikan hadiah atau janji tersebut ada hubungan dengan jabatannya.

Pasal 12:
Dipidana dengan pidana penjara seumur hidup atau pidana penjara paling singkat 4 (empat) tahun dan paling lama 20 (dua puluh) tahun dan pidana denda paling sedikit Rp 200.000.000,00 (dua ratus juta rupiah) dan paling banyak Rp 1.000.000.000,00 (satu milyar rupiah):
a. pegawai negeri atau penyelenggara negara yang menerima hadiah atau janji, padahal diketahui atau patut diduga bahwa hadiah atau janji tersebut diberikan untuk menggerakkan agar melakukan atau tidak melakukan sesuatu dalam jabatannya, yang bertentangan dengan kewajibannya;
b. pegawai negeri atau penyelenggara negara yang menerima hadiah, padahal diketahui atau patut diduga bahwa hadiah tersebut diberikan sebagai akibat atau disebabkan karena telah melakukan atau tidak melakukan sesuatu dalam jabatannya yang bertentangan dengan kewajibannya.

Pasal 12B (Gratifikasi):
(1) Setiap gratifikasi kepada pegawai negeri atau penyelenggara negara dianggap pemberian suap, apabila berhubungan dengan jabatannya dan yang berlawanan dengan kewajiban atau tugasnya.
(2) Pidana bagi pegawai negeri atau penyelenggara negara sebagaimana dimaksud dalam ayat (1) adalah pidana penjara seumur hidup atau pidana penjara paling singkat 4 (empat) tahun dan paling lama 20 (dua puluh) tahun, dan pidana denda paling sedikit Rp 200.000.000,00 (dua ratus juta rupiah) dan paling banyak Rp 1.000.000.000,00 (satu milyar rupiah).
        """,
        "articles": [
            {"number": "Pasal 2", "content": "Perbuatan melawan hukum memperkaya diri yang merugikan keuangan negara. Pidana penjara 4-20 tahun atau seumur hidup, denda Rp200juta-Rp1milyar."},
            {"number": "Pasal 3", "content": "Penyalahgunaan kewenangan/jabatan yang merugikan keuangan negara. Pidana penjara 1-20 tahun atau seumur hidup, denda Rp50juta-Rp1milyar."},
            {"number": "Pasal 5", "content": "Memberi/menjanjikan sesuatu kepada pegawai negeri agar berbuat/tidak berbuat sesuatu. Pidana penjara 1-5 tahun, denda Rp50juta-Rp250juta."},
            {"number": "Pasal 11", "content": "Pegawai negeri menerima hadiah/janji terkait jabatannya. Pidana penjara 1-5 tahun, denda Rp50juta-Rp250juta."},
            {"number": "Pasal 12", "content": "Pegawai negeri menerima hadiah untuk melakukan/tidak melakukan sesuatu bertentangan kewajiban. Pidana 4-20 tahun atau seumur hidup."},
            {"number": "Pasal 12B", "content": "Gratifikasi kepada pegawai negeri dianggap suap jika berhubungan jabatan. Pidana 4-20 tahun atau seumur hidup, denda Rp200juta-Rp1milyar."},
        ]
    },
    
    "PP_DISIPLIN_PNS": {
        "title": "PP 94/2021 tentang Disiplin Pegawai Negeri Sipil",
        "short_name": "PP Disiplin PNS",
        "category": "MISCONDUCT",
        "full_text": """
PERATURAN PEMERINTAH REPUBLIK INDONESIA NOMOR 94 TAHUN 2021 TENTANG DISIPLIN PEGAWAI NEGERI SIPIL

BAB II - KEWAJIBAN DAN LARANGAN

Pasal 3 - Kewajiban PNS:
Setiap PNS wajib:
a. setia dan taat sepenuhnya kepada Pancasila, UUD 1945, NKRI, dan Pemerintah;
b. menjaga persatuan dan kesatuan bangsa;
c. melaksanakan kebijakan yang ditetapkan oleh pejabat pemerintah yang berwenang;
d. menaati ketentuan peraturan perundang-undangan;
e. melaksanakan tugas kedinasan dengan penuh pengabdian, kejujuran, kesadaran, dan tanggung jawab;
f. menunjukkan integritas dan keteladanan dalam sikap, perilaku, ucapan, dan tindakan;
g. menyimpan rahasia jabatan;
h. bersedia ditempatkan di seluruh wilayah NKRI;
i. mengutamakan kepentingan negara daripada kepentingan pribadi, seseorang, dan/atau golongan;
j. melaporkan harta kekayaan kepada pejabat berwenang;
k. masuk kerja dan menaati ketentuan jam kerja;
l. mencapai sasaran kerja pegawai yang ditetapkan;
m. menggunakan dan memelihara barang milik negara dengan sebaik-baiknya;
n. memberikan kesempatan kepada bawahan untuk mengembangkan kompetensi;
o. menolak segala bentuk pemberian yang berkaitan dengan tugas dan fungsi.

Pasal 4 - Larangan PNS:
Setiap PNS dilarang:
a. menyalahgunakan wewenang;
b. menjadi perantara untuk mendapatkan keuntungan pribadi dengan menggunakan kewenangan orang lain;
c. memiliki, menjual, membeli, menggadaikan, menyewakan, atau meminjamkan barang milik negara secara tidak sah;
d. melakukan pungutan di luar ketentuan;
e. melakukan kegiatan yang merugikan negara;
f. bertindak sewenang-wenang terhadap bawahan;
g. menghalangi berjalannya tugas kedinasan;
h. menerima hadiah yang berhubungan dengan jabatan dan/atau pekerjaannya;
i. meminta sesuatu yang berhubungan dengan jabatan;
j. melakukan tindakan atau tidak melakukan tindakan yang dapat menghalangi atau mempersulit salah satu pihak yang dilayani.

BAB III - HUKUMAN DISIPLIN

Pasal 7 - Jenis Hukuman:
(1) Tingkat hukuman disiplin terdiri atas:
    a. hukuman disiplin ringan;
    b. hukuman disiplin sedang; dan
    c. hukuman disiplin berat.

(2) Jenis hukuman disiplin ringan terdiri atas:
    a. teguran lisan;
    b. teguran tertulis; dan
    c. pernyataan tidak puas secara tertulis.

(3) Jenis hukuman disiplin sedang terdiri atas:
    a. pemotongan tunjangan kinerja sebesar 25% selama 6 bulan;
    b. pemotongan tunjangan kinerja sebesar 25% selama 9 bulan; dan
    c. pemotongan tunjangan kinerja sebesar 25% selama 12 bulan.

(4) Jenis hukuman disiplin berat terdiri atas:
    a. penurunan jabatan setingkat lebih rendah selama 12 bulan;
    b. pembebasan dari jabatannya menjadi jabatan pelaksana selama 12 bulan; dan
    c. pemberhentian dengan hormat tidak atas permintaan sendiri sebagai PNS.
        """,
        "articles": [
            {"number": "Pasal 3", "content": "Kewajiban PNS: setia pada Pancasila/UUD, taat peraturan, jujur, berintegritas, menjaga rahasia jabatan, menolak pemberian terkait tugas."},
            {"number": "Pasal 4", "content": "Larangan PNS: menyalahgunakan wewenang, menjadi perantara keuntungan pribadi, pungutan liar, menerima hadiah terkait jabatan, mempersulit pelayanan."},
            {"number": "Pasal 7", "content": "Hukuman disiplin: ringan (teguran), sedang (potong tunjangan 25% 6-12 bulan), berat (penurunan jabatan/pemberhentian)."},
        ]
    },
    
    "PERPRES_PBJ": {
        "title": "Perpres 16/2018 tentang Pengadaan Barang/Jasa Pemerintah",
        "short_name": "Perpres PBJ",
        "category": "PROCUREMENT",
        "full_text": """
PERATURAN PRESIDEN REPUBLIK INDONESIA NOMOR 16 TAHUN 2018 TENTANG PENGADAAN BARANG/JASA PEMERINTAH

BAB II - PRINSIP DAN ETIKA PENGADAAN

Pasal 6 - Prinsip Pengadaan:
Pengadaan Barang/Jasa menerapkan prinsip sebagai berikut:
a. efisien;
b. efektif;
c. transparan;
d. terbuka;
e. bersaing;
f. adil; dan
g. akuntabel.

Pasal 7 - Etika Pengadaan:
(1) Semua pihak yang terlibat dalam Pengadaan Barang/Jasa mematuhi etika sebagai berikut:
    a. melaksanakan tugas secara tertib, disertai rasa tanggung jawab untuk mencapai sasaran, kelancaran, dan ketepatan tujuan Pengadaan Barang/Jasa;
    b. bekerja secara profesional, mandiri, dan menjaga kerahasiaan informasi;
    c. tidak saling mempengaruhi baik langsung maupun tidak langsung yang berakibat persaingan usaha tidak sehat;
    d. menerima dan bertanggung jawab atas segala keputusan yang ditetapkan sesuai dengan kesepakatan tertulis pihak yang terkait;
    e. menghindari dan mencegah terjadinya pertentangan kepentingan pihak yang terkait, baik secara langsung maupun tidak langsung, yang berakibat persaingan usaha tidak sehat;
    f. menghindari dan mencegah pemborosan dan kebocoran keuangan negara;
    g. menghindari dan mencegah penyalahgunaan wewenang dan/atau kolusi; dan
    h. tidak menerima, tidak menawarkan, atau tidak menjanjikan untuk memberi atau menerima hadiah, imbalan, komisi, rabat, dan/atau berupa apa saja.

BAB X - SANKSI

Pasal 78:
(1) Perbuatan atau tindakan Penyedia yang dapat dikenakan sanksi adalah:
    a. berusaha mempengaruhi Pokja Pemilihan/Pejabat Pengadaan/pihak lain yang berwenang dalam bentuk dan cara apapun;
    b. melakukan persekongkolan dengan Penyedia lain untuk mengatur harga penawaran;
    c. membuat dan/atau menyampaikan dokumen dan/atau keterangan lain yang tidak benar;
    d. mengundurkan diri dengan alasan yang tidak dapat diterima;
    e. tidak dapat menyelesaikan pekerjaan sesuai dengan Kontrak;
    f. menyalahgunakan fasilitas yang diberikan;
    g. berperilaku tidak baik;
    h. melanggar ketentuan peraturan perundang-undangan.

(2) Selain perbuatan sebagaimana dimaksud pada ayat (1), perbuatan Penyedia yang dapat dikenakan sanksi berupa sanksi daftar hitam adalah:
    a. tidak melaksanakan Kontrak, tidak menyelesaikan pekerjaan, atau tidak melaksanakan kewajiban dalam masa pemeliharaan;
    b. menyebabkan kegagalan bangunan;
    c. menyerahkan Jaminan yang tidak dapat dicairkan;
    d. terindikasi melakukan persekongkolan, korupsi, kolusi, dan/atau nepotisme.
        """,
        "articles": [
            {"number": "Pasal 6", "content": "Prinsip pengadaan: efisien, efektif, transparan, terbuka, bersaing, adil, akuntabel."},
            {"number": "Pasal 7", "content": "Etika pengadaan: profesional, tidak mempengaruhi persaingan, mencegah pertentangan kepentingan, tidak menerima/memberi hadiah/komisi."},
            {"number": "Pasal 78", "content": "Sanksi penyedia: mempengaruhi pokja, persekongkolan harga, dokumen palsu, tidak selesaikan kontrak. Daftar hitam untuk persekongkolan/KKN."},
        ]
    },
    
    "UU_PDP": {
        "title": "UU 27/2022 tentang Pelindungan Data Pribadi",
        "short_name": "UU PDP",
        "category": "DATA_BREACH",
        "full_text": """
UNDANG-UNDANG REPUBLIK INDONESIA NOMOR 27 TAHUN 2022 TENTANG PELINDUNGAN DATA PRIBADI

BAB IV - HAK SUBJEK DATA PRIBADI

Pasal 5:
Subjek Data Pribadi berhak:
a. mendapatkan Informasi tentang kejelasan identitas, dasar kepentingan hukum, tujuan permintaan dan penggunaan Data Pribadi, dan akuntabilitas pihak yang meminta Data Pribadi;
b. melengkapi, memperbarui, dan/atau memperbaiki kesalahan dan/atau ketidakakuratan Data Pribadi tentang dirinya sesuai dengan tujuan pemrosesan Data Pribadi;
c. mendapatkan akses dan memperoleh salinan Data Pribadi tentang dirinya sesuai dengan ketentuan peraturan perundang-undangan;
d. mengakhiri pemrosesan, menghapus, dan/atau memusnahkan Data Pribadi tentang dirinya.

BAB V - KEWAJIBAN PENGENDALI DATA PRIBADI

Pasal 20:
Pengendali Data Pribadi wajib:
a. melakukan pemrosesan Data Pribadi secara terbatas dan spesifik, sah secara hukum, dan transparan;
b. memastikan keamanan pemrosesan Data Pribadi;
c. melakukan pengawasan terhadap setiap pihak yang terlibat dalam pemrosesan Data Pribadi;
d. melindungi Data Pribadi dari pemrosesan yang tidak sah.

Pasal 46:
(1) Dalam hal terjadi kegagalan Pelindungan Data Pribadi, Pengendali Data Pribadi wajib menyampaikan pemberitahuan secara tertulis paling lambat 3 x 24 jam kepada:
    a. Subjek Data Pribadi; dan
    b. lembaga.

BAB XIV - KETENTUAN PIDANA

Pasal 67:
(1) Setiap Orang yang dengan sengaja dan melawan hukum memperoleh atau mengumpulkan Data Pribadi yang bukan miliknya dengan maksud untuk menguntungkan diri sendiri atau orang lain yang dapat mengakibatkan kerugian Subjek Data Pribadi dipidana dengan pidana penjara paling lama 5 (lima) tahun dan/atau pidana denda paling banyak Rp5.000.000.000,00 (lima miliar rupiah).

Pasal 68:
Setiap Orang yang dengan sengaja dan melawan hukum mengungkapkan Data Pribadi yang bukan miliknya dipidana dengan pidana penjara paling lama 4 (empat) tahun dan/atau pidana denda paling banyak Rp4.000.000.000,00 (empat miliar rupiah).

Pasal 69:
Setiap Orang yang dengan sengaja dan melawan hukum menggunakan Data Pribadi yang bukan miliknya dipidana dengan pidana penjara paling lama 5 (lima) tahun dan/atau pidana denda paling banyak Rp5.000.000.000,00 (lima miliar rupiah).

Pasal 70:
Setiap Orang yang dengan sengaja dan melawan hukum membuat Data Pribadi palsu atau memalsukan Data Pribadi dengan maksud untuk menguntungkan diri sendiri atau orang lain yang dapat mengakibatkan kerugian bagi orang lain dipidana dengan pidana penjara paling lama 6 (enam) tahun dan/atau pidana denda paling banyak Rp6.000.000.000,00 (enam miliar rupiah).
        """,
        "articles": [
            {"number": "Pasal 5", "content": "Hak subjek data: informasi kejelasan identitas, melengkapi/memperbaiki data, akses salinan data, mengakhiri/menghapus data."},
            {"number": "Pasal 20", "content": "Kewajiban pengendali: pemrosesan terbatas/spesifik/transparan, keamanan data, pengawasan, lindungi dari pemrosesan tidak sah."},
            {"number": "Pasal 46", "content": "Kegagalan pelindungan wajib dilaporkan 3x24 jam kepada subjek data dan lembaga."},
            {"number": "Pasal 67-70", "content": "Pidana: memperoleh data melawan hukum 5 tahun/Rp5M, mengungkapkan 4 tahun/Rp4M, menggunakan 5 tahun/Rp5M, memalsukan 6 tahun/Rp6M."},
        ]
    },
    
    "ISO_37002": {
        "title": "ISO 37002:2021 Whistleblowing Management Systems",
        "short_name": "ISO 37002",
        "category": "ETHICS",
        "full_text": """
ISO 37002:2021 WHISTLEBLOWING MANAGEMENT SYSTEMS - GUIDELINES

1. SCOPE
This document gives guidelines for implementing, managing, evaluating, maintaining and improving a robust and effective whistleblowing management system within an organization.

2. PRINCIPLES
A whistleblowing management system should be based on the following principles:
a) Trust: The system should be designed to encourage reports of wrongdoing by building trust with stakeholders.
b) Impartiality: Reports should be assessed and addressed objectively and fairly.
c) Protection: Persons who report wrongdoing in good faith should be protected from retaliation.
d) Confidentiality: The identity of the whistleblower should be protected to the extent possible.

3. WHISTLEBLOWING PROCESS

3.1 Receiving Reports
Organizations should establish accessible and secure channels for receiving reports of wrongdoing. These can include:
- Dedicated telephone hotlines
- Email addresses
- Online reporting platforms
- In-person reporting mechanisms
- Written correspondence

3.2 Assessing Reports
Each report should be assessed to determine:
- Whether it falls within the scope of the whistleblowing management system
- The severity and potential impact of the alleged wrongdoing
- The appropriate response and investigation requirements
- Priority level based on urgency and risk

3.3 Addressing Reports
Organizations should:
- Acknowledge receipt of the report
- Investigate allegations thoroughly and impartially
- Take appropriate corrective action
- Document all steps taken
- Maintain communication with the whistleblower where possible

3.4 Closing Cases
Cases should be closed when:
- The investigation is complete
- Appropriate action has been taken
- All documentation is finalized
- The whistleblower has been informed of the outcome (where appropriate)

4. PROTECTION OF WHISTLEBLOWERS

4.1 Confidentiality
- Protect the identity of the whistleblower
- Limit access to case information on a need-to-know basis
- Use secure systems for storing and transmitting information

4.2 Protection from Retaliation
- Prohibit any form of retaliation against whistleblowers
- Monitor for signs of retaliation
- Take swift action to address any retaliation
- Provide support to whistleblowers who experience retaliation

5. GOVERNANCE AND OVERSIGHT

5.1 Leadership
Top management should demonstrate commitment to the whistleblowing management system by:
- Establishing a whistleblowing policy
- Allocating adequate resources
- Promoting a speak-up culture
- Ensuring regular review and improvement

5.2 Roles and Responsibilities
Clear roles should be defined for:
- Receiving and triaging reports
- Investigating allegations
- Making decisions on corrective actions
- Overseeing the system
- Reporting to the board/governing body
        """,
        "articles": [
            {"number": "Principles", "content": "Prinsip WBS: Trust (kepercayaan), Impartiality (ketidakberpihakan), Protection (perlindungan), Confidentiality (kerahasiaan)."},
            {"number": "Receiving", "content": "Kanal penerimaan: hotline telepon, email, platform online, tatap muka, surat tertulis."},
            {"number": "Assessing", "content": "Penilaian: cakupan WBS, tingkat keparahan, kebutuhan investigasi, prioritas berdasarkan urgensi/risiko."},
            {"number": "Addressing", "content": "Penanganan: acknowledge laporan, investigasi menyeluruh, tindakan korektif, dokumentasi, komunikasi dengan pelapor."},
            {"number": "Protection", "content": "Perlindungan pelapor: jaga kerahasiaan identitas, batasi akses info, larang retaliasi, monitor tanda-tanda retaliasi."},
            {"number": "Governance", "content": "Tata kelola: komitmen pimpinan, alokasi sumber daya, budaya speak-up, review dan perbaikan berkala."},
        ]
    }
}


# ============== Embedding Service ==============

class SimpleEmbedding:
    """Simple embedding using hash-based approach for seeding"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    def embed(self, text: str) -> list:
        """Generate pseudo-embedding from text hash"""
        import hashlib
        
        # Create hash
        text_hash = hashlib.sha384(text.encode('utf-8')).digest()
        
        # Convert to floats
        embedding = []
        for i in range(self.dimension):
            byte_val = text_hash[i % len(text_hash)]
            embedding.append((byte_val / 255.0) * 2 - 1)
        
        # Normalize
        magnitude = sum(x*x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding


try:
    from sentence_transformers import SentenceTransformer
    
    class TransformerEmbedding:
        """Sentence transformer embedding"""
        
        def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
        
        def embed(self, text: str) -> list:
            """Generate embedding from text"""
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
    
    EmbeddingService = TransformerEmbedding
    
except ImportError:
    logger.warning("sentence-transformers not available, using simple embedding")
    EmbeddingService = SimpleEmbedding


# ============== Text Chunking ==============

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks"""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end
            for punct in ['. ', '.\n', ';\n', ':\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct > start + chunk_size // 2:
                    end = last_punct + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


# ============== Database Operations ==============

async def clear_knowledge_base():
    """Clear existing knowledge vectors"""
    logger.info("Clearing existing knowledge base...")
    
    try:
        supabase.table("knowledge_vectors").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        logger.info("Knowledge base cleared")
    except Exception as e:
        logger.warning(f"Could not clear knowledge base: {e}")


async def insert_vector(embedding_service, doc_id: str, title: str, content: str, metadata: dict):
    """Insert a single vector into database"""
    try:
        # Generate embedding
        embedding = embedding_service.embed(content)
        
        # Insert into database
        data = {
            "doc_id": doc_id,
            "title": title,
            "content": content,
            "embedding": embedding,
            "metadata": metadata
        }
        
        supabase.table("knowledge_vectors").insert(data).execute()
        return True
        
    except Exception as e:
        logger.error(f"Failed to insert vector: {e}")
        return False


async def seed_regulation(embedding_service, reg_key: str, regulation: dict) -> tuple:
    """Seed a single regulation into the knowledge base"""
    
    documents_loaded = 0
    chunks_created = 0
    
    logger.info(f"Processing: {regulation['title']}")
    
    # 1. Index full document
    full_chunks = chunk_text(regulation['full_text'])
    
    for i, chunk in enumerate(full_chunks):
        success = await insert_vector(
            embedding_service,
            doc_id=f"{reg_key}_full_{i}",
            title=regulation['title'],
            content=chunk,
            metadata={
                "regulation": reg_key,
                "type": "full_text",
                "category": regulation['category'],
                "chunk_index": i,
                "total_chunks": len(full_chunks)
            }
        )
        if success:
            chunks_created += 1
    
    documents_loaded += 1
    
    # 2. Index individual articles
    for article in regulation.get('articles', []):
        success = await insert_vector(
            embedding_service,
            doc_id=f"{reg_key}_{article['number'].replace(' ', '_')}",
            title=f"{regulation['short_name']} - {article['number']}",
            content=article['content'],
            metadata={
                "regulation": reg_key,
                "type": "article",
                "article_number": article['number'],
                "category": regulation['category']
            }
        )
        if success:
            chunks_created += 1
            documents_loaded += 1
    
    logger.info(f"  → {documents_loaded} documents, {chunks_created} chunks")
    
    return documents_loaded, chunks_created


async def seed_all_regulations(reset: bool = False):
    """Seed all pre-loaded regulations"""
    
    logger.info("=" * 60)
    logger.info("WBS BPKH AI - Knowledge Base Seeder")
    logger.info("=" * 60)
    
    if reset:
        await clear_knowledge_base()
    
    # Initialize embedding service
    embedding_service = EmbeddingService()
    logger.info(f"Embedding dimension: {embedding_service.dimension}")
    
    total_documents = 0
    total_chunks = 0
    
    for reg_key, regulation in REGULATIONS.items():
        docs, chunks = await seed_regulation(embedding_service, reg_key, regulation)
        total_documents += docs
        total_chunks += chunks
    
    logger.info("=" * 60)
    logger.info(f"COMPLETE: {total_documents} documents, {total_chunks} chunks indexed")
    logger.info("=" * 60)
    
    return {
        "status": "success",
        "documents_loaded": total_documents,
        "chunks_created": total_chunks,
        "regulations": list(REGULATIONS.keys())
    }


# ============== Main ==============

def main():
    parser = argparse.ArgumentParser(description="WBS BPKH AI Knowledge Base Seeder")
    parser.add_argument("--reset", action="store_true", help="Clear existing knowledge base before seeding")
    args = parser.parse_args()
    
    result = asyncio.run(seed_all_regulations(reset=args.reset))
    
    print("\n" + "=" * 60)
    print("Seeding Complete!")
    print(f"Documents: {result['documents_loaded']}")
    print(f"Chunks: {result['chunks_created']}")
    print(f"Regulations: {', '.join(result['regulations'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
