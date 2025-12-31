# 🛡️ WBS BPKH AI - Whistleblowing System

<div align="center">

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Status](https://img.shields.io/badge/status-Production_Ready-brightgreen)

**Sistem Pelaporan Pelanggaran Berbasis AI untuk Badan Pengelola Keuangan Haji**

[Demo](#demo) • [Instalasi](#instalasi) • [Dokumentasi](#dokumentasi) • [API](#api-endpoints)

</div>

---

## 📋 Overview

**WBS BPKH AI** adalah platform whistleblowing modern yang memungkinkan:
- ✅ Pelaporan anonim dugaan pelanggaran/fraud
- ✅ Komunikasi dua arah antara pelapor dan pengelola
- ✅ Analisis otomatis menggunakan AI Multi-Agent
- ✅ Pelacakan status laporan secara real-time
- ✅ RAG (Retrieval Augmented Generation) dengan knowledge base regulasi

### Standar Kepatuhan
- **ISO 37002:2021** - Whistleblowing Management Systems
- **PKBP 8/2022** - Tata Cara Pengelolaan WBS BPKH
- **UU No. 31/2014** - Perlindungan Saksi dan Korban

---

## 📞 Channel Pelaporan

| Channel | Kontak | Keterangan |
|---------|--------|------------|
| 🌐 Web Portal | wbs.bpkh.go.id | Form online dengan AI analysis |
| 📱 WhatsApp (Utama) | +62 853-19000-230 | Chat langsung, auto-reply ID tiket |
| 📱 WhatsApp (Cadangan) | +62 853-19000-140 | Nomor cadangan |
| ✉️ Email | wbs@bpkh.go.id | Pelaporan via email |

---

## 👥 Stakeholders

| Stakeholder | Peran | Akses |
|-------------|-------|-------|
| Pelapor | Melaporkan dugaan pelanggaran | Web Portal / WhatsApp / Email |
| Pengelola WBS (UP1) | Menindaklanjuti laporan | Dashboard Admin |
| Bidang Audit Internal | Audit investigatif | Dashboard AI |
| Super Admin | Manajemen sistem & user | Dashboard Admin (Full) |
| Pimpinan | Review hasil investigasi | Dashboard / Report |

---

## 🏗️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Web Portal    │  WhatsApp Bot   │     Admin Dashboard         │
│  (Pelaporan)    │   (via WAHA)    │    (Pengelola WBS)          │
└────────┬────────┴────────┬────────┴────────────┬────────────────┘
         │                 │                      │
         └─────────────────┼──────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                    BACKEND LAYER (FastAPI)                       │
├──────────────────────────┼──────────────────────────────────────┤
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │               AI ANALYSIS ENGINE                          │  │
│  │  ┌─────────────┬─────────────┬─────────────────────────┐  │  │
│  │  │  Context    │  Severity   │   Fraud     │  Similar  │  │  │
│  │  │  Retriever  │  Analyzer   │   Detector  │  Finder   │  │  │
│  │  ├─────────────┼─────────────┼─────────────┼───────────┤  │  │
│  │  │  Compliance │   Summary   │  Finalizer  │  (RAG)    │  │  │
│  │  │  Checker    │  Generator  │             │           │  │  │
│  │  └─────────────┴─────────────┴─────────────┴───────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                     DATA LAYER                                   │
├──────────────────────────┼──────────────────────────────────────┤
│    Supabase PostgreSQL   │      pgvector / ChromaDB             │
│    (Reports, Messages,   │      (Embeddings, RAG)               │
│     Audit Logs)          │                                      │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## 🔄 Alur Proses Bisnis

```
BARU → SEDANG DITINJAU → BUTUH INFO (opsional) → DALAM INVESTIGASI → SELESAI
```

| No | Tahap | Kegiatan |
|----|-------|----------|
| 1 | Penerimaan Laporan | Sistem mencatat laporan dan menghasilkan ID Tiket |
| 2 | Review Awal | UP1/Pengelola menelaah laporan & hasil analisis AI |
| 3 | Update Status | Status menjadi Sedang Ditinjau / Butuh Info |
| 4 | Komunikasi | Klarifikasi dengan pelapor via Web Portal / WhatsApp |
| 5 | Eskalasi Investigasi | Laporan layak diteruskan ke Bidang Audit Internal |
| 6 | Investigasi | Audit Internal melakukan investigasi |
| 7 | Keputusan | Hasil: Terbukti / Tidak Terbukti / Rekomendasi |
| 8 | Notifikasi | UP1 menyampaikan pokok hasil ke pelapor |

---

## 📊 Status Laporan

| Status | Deskripsi |
|--------|-----------|
| 🔵 Baru - Via Web | Laporan baru masuk dari portal web |
| 🔵 Baru - Via WhatsApp | Laporan baru masuk dari WhatsApp |
| 🟡 Sedang Ditinjau | Pengelola sedang mereview laporan |
| 🟣 Butuh Informasi | Menunggu informasi tambahan dari pelapor |
| 🔴 Dalam Investigasi | Proses investigasi sedang berjalan |
| ⬛ Ditingkatkan | Laporan dieskalasi ke level yang lebih tinggi |
| ⚪ Hold | Laporan ditunda sementara |
| 🟢 Selesai - Terbukti | Pelanggaran terbukti, tindak lanjut dilakukan |
| ⚫ Selesai - Tidak Terbukti | Bukti tidak cukup, laporan diarsipkan |

---

## ⚠️ Kategori Pelanggaran

| No | Jenis | Dasar Hukum |
|----|-------|-------------|
| 1 | Korupsi | KUHP Pasal 2, 3 \| UU Tipikor |
| 2 | Gratifikasi / Penyuapan | UU No. 11 Tahun 1980 |
| 3 | Penggelapan | KUHP Pasal 372 |
| 4 | Penipuan | KUHP Pasal 378 |
| 5 | Pencurian | KUHP Pasal 362 |
| 6 | Pemerasan | KUHP Pasal 368 |
| 7 | Benturan Kepentingan | UU No. 30/2014 |
| 8 | Pelanggaran Kebijakan | SOP Internal BPKH |
| 9 | Tindakan Curang | Kode Etik BPKH |

---

## ⏱️ Service Level Agreement (SLA)

| Severity | Initial Response | Investigation | Resolution |
|----------|-----------------|---------------|------------|
| 🔴 **CRITICAL** | < 4 jam | < 24 jam | < 7 hari |
| 🟠 **HIGH** | < 24 jam | < 3 hari | < 14 hari |
| 🟡 **MEDIUM** | < 3 hari | < 7 hari | < 30 hari |
| 🟢 **LOW** | < 7 hari | < 14 hari | < 60 hari |

### Kriteria Severity

| Level | Kriteria |
|-------|----------|
| CRITICAL | Kerugian > Rp 1 Miliar, Pejabat tinggi |
| HIGH | Kerugian Rp 100 Juta - 1 Miliar |
| MEDIUM | Kerugian Rp 10 - 100 Juta |
| LOW | Kerugian < Rp 10 Juta |

---

## 🤖 AI Analysis Engine

### Multi-Agent Architecture

| Agent | Fungsi |
|-------|--------|
| **Context Retriever** | Mengambil konteks relevan dari knowledge base |
| **Severity Analyzer** | Menilai tingkat keparahan (Critical/High/Medium/Low) |
| **Fraud Detector** | Mendeteksi indikasi fraud berdasarkan pola |
| **Similar Finder** | Mencari kasus serupa dari database |
| **Compliance Checker** | Memeriksa kepatuhan terhadap regulasi |
| **Summary Generator** | Merangkum hasil analisis |
| **Finalizer** | Menghasilkan output final dengan rekomendasi |

### Output Analisis

- **Severity Level** - Tingkat keparahan dengan SLA otomatis
- **Category** - Klasifikasi jenis pelanggaran dengan dasar hukum
- **Fraud Score (0-1)** - Indikasi risiko fraud
  - 0.00-0.30: Indikasi Rendah
  - 0.31-0.70: Indikasi Sedang
  - 0.71-1.00: Indikasi Tinggi
- **Compliance Status** - Regulasi yang berpotensi dilanggar
- **Similar Cases** - Kasus serupa dari database
- **Recommended Actions** - Rekomendasi tindakan

---

## 📈 Escalation Matrix

| Level | Pihak | Kondisi Eskalasi |
|-------|-------|------------------|
| 1 | Pengelola WBS | Penanganan standar |
| 2 | Kepala Unit WBS | SLA breach atau severity Critical |
| 3 | Anggota BP (Kepatuhan) | Pejabat eselon atau kerugian > 500 Juta |
| 4 | Dewan Pengawas | Direksi atau kerugian > 1 Miliar |

---

## 🚀 Instalasi

### Prerequisites

- Python 3.10+
- Node.js 18+ (untuk WAHA)
- PostgreSQL 14+ atau Supabase account

### Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd wbs-bpkh-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env dengan kredensial Anda

# 5. Setup database
# Jalankan scripts/setup_supabase.sql di Supabase SQL Editor

# 6. Load knowledge base
python scripts/seed_knowledge.py

# 7. Run backend
cd backend
uvicorn main:app --reload --port 8000

# 8. Open frontend
# Admin: frontend/wbs_dashboard.html
# Public: frontend/portal_pelaporan.html
```

### Environment Variables

```env
# Groq API
GROQ_API_KEY=your_groq_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# WhatsApp (WAHA)
WAHA_API_URL=http://localhost:3000
WAHA_SESSION=default
WAHA_NUMBER_PRIMARY=+6285319000230
WAHA_NUMBER_BACKUP=+6285319000140

# Email
WBS_EMAIL=wbs@bpkh.go.id
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=password
```

---

## 📁 Struktur Project

```
wbs-bpkh-ai/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py      # Multi-agent orchestrator
│   │   ├── intake_agent.py      # 4W+1H parsing
│   │   ├── analysis_agent.py    # Fraud triangle analysis
│   │   ├── compliance_agent.py  # Regulation matching
│   │   ├── severity_agent.py    # Risk assessment
│   │   ├── recommendation_agent.py
│   │   └── summary_agent.py
│   ├── rag/
│   │   ├── embeddings.py        # Sentence transformers
│   │   ├── retriever.py         # Vector search
│   │   └── knowledge_loader.py  # Regulation loader
│   ├── models/
│   │   └── __init__.py          # Pydantic models
│   ├── config.py                # Configuration
│   ├── database.py              # Supabase client
│   └── main.py                  # FastAPI app
├── frontend/
│   ├── wbs_dashboard.html       # Admin dashboard
│   └── portal_pelaporan.html    # Public portal
├── docs/
│   ├── business_process_wbs_bpkh.html  # Business process documentation
│   └── business_process_flow.html      # Flow diagram
├── scripts/
│   ├── setup_supabase.sql       # Database schema
│   └── seed_knowledge.py        # Knowledge base seeder
├── knowledge_base/              # Custom documents
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reports` | Submit new report |
| GET | `/api/v1/reports` | List all reports |
| GET | `/api/v1/reports/{id}` | Get report details |
| PATCH | `/api/v1/reports/{id}/status` | Update status |

### Tickets (Anonymous)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tickets/lookup` | Lookup by ticket ID |
| POST | `/api/v1/tickets/{id}/messages` | Send message |
| GET | `/api/v1/tickets/{id}/messages` | Get messages |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analysis/run` | Run AI analysis |
| GET | `/api/v1/analysis/{id}` | Get analysis result |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/stats` | Get dashboard stats |

### Reference Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/reference/statuses` | Get all statuses |
| GET | `/api/v1/reference/severities` | Get severity levels |
| GET | `/api/v1/reference/categories` | Get violation categories |

---

## 🔒 Keamanan

### Prinsip Keamanan
- **Anonimitas** - Identitas pelapor dilindungi
- **Enkripsi** - HTTPS, database encrypted at rest
- **Access Control** - Role-based access control
- **Perlindungan Pelapor** - Sesuai UU No. 31/2014

### User Roles
| Role | Akses | Kemampuan |
|------|-------|-----------|
| PELAPOR | Web Portal, WhatsApp | Buat laporan, tracking, chat |
| PENGELOLA | Dashboard Admin | Kelola laporan, update, balas |
| SUPER_ADMIN | Full Access | Semua + user management |

---

## 📚 Knowledge Base (RAG)

### Pre-loaded Regulations
1. **UU 31/1999 jo UU 20/2001** - Tindak Pidana Korupsi
2. **PP 94/2021** - Disiplin Pegawai Negeri Sipil
3. **Perpres 16/2018** - Pengadaan Barang/Jasa
4. **UU 27/2022** - Perlindungan Data Pribadi
5. **ISO 37002:2021** - Whistleblowing Management Systems

### Menambah Dokumen Custom
```bash
# Letakkan dokumen di folder knowledge_base/
# Jalankan seeder
python scripts/seed_knowledge.py
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Groq API (llama-3.3-70b-versatile) |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | sentence-transformers (local) |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Frontend | HTML5, TailwindCSS, Chart.js |
| Data Models | Pydantic v2 |
| Logging | Loguru |

---

## 📄 Dokumen Terkait

- Kode Etik BPKH
- SOP Penanganan Pengaduan
- UU No. 31/2014 - Perlindungan Saksi Dan Korban
- UU No. 20/2001 - Pemberantasan Tindak Pidana Korupsi
- PKBP 8/2022 - Tata Cara Pengelolaan WBS BPKH
- PKBP 13/2024 - Pedoman Audit Khusus BPKH

---

## 👥 Tim Penyusun

**Disusun oleh:**
- M. Sopian Hadianto
- Irham Yusnadi
- Ismail

**Disetujui oleh:**
- **ROJIKIN** - Ketua Komite Audit

---

## 📝 Changelog

### v1.1.0 (Desember 2025)
- ✅ Multi-agent AI analysis engine
- ✅ RAG dengan 5 regulasi pre-loaded
- ✅ Unified inbox untuk komunikasi dua arah
- ✅ Dashboard admin dengan real-time stats
- ✅ Public portal untuk pelaporan anonim
- ✅ SLA management otomatis
- ✅ Escalation matrix
- ✅ Audit trail lengkap

---

## 📜 License

Dokumen ini adalah properti BPKH. All rights reserved.

---

<div align="center">

**Versi 1.1 | Desember 2025**

*Whistleblowing System - Badan Pengelola Keuangan Haji*

</div>
