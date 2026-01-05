"""
WBS BPKH AI - Configuration Module
=================================
Centralized configuration management using Pydantic Settings.
Based on: Business Process WBS BPKH v1.1 (Desember 2025)
Authors: M. Sopian Hadianto, Irham Yusnadi, Ismail
Approved by: Rojikin (Ketua Komite Audit)
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional, Dict, Any
from functools import lru_cache
import os
from enum import Enum

class Settings(BaseSettings):
    """Application Settings"""
    
    # Application
    app_name: str = Field(default="WBS BPKH AI", env="APP_NAME")
    app_version: str = Field(default="1.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(default="", env="SECRET_KEY")  # Must be set in production
    
    # Groq API
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    llm_model: str = Field(default="llama-3.3-70b-versatile", env="LLM_MODEL")
    embedding_model: str = Field(default="llama-3.3-70b-versatile", env="EMBEDDING_MODEL")
    max_tokens: int = Field(default=4096, env="MAX_TOKENS")
    temperature: float = Field(default=0.1, env="TEMPERATURE")
    
    # Supabase
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    supabase_service_key: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    
    # Security
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "https://wbs.bpkh.go.id"],
        env="CORS_ORIGINS"
    )
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")

    # JWT Authentication
    jwt_secret: str = Field(default="", env="JWT_SECRET")  # Must be set in production
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiry_minutes: int = Field(default=60, env="JWT_EXPIRY_MINUTES")  # 1 hour
    
    # Notification
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    
    # WhatsApp (WAHA)
    waha_api_url: Optional[str] = Field(default=None, env="WAHA_API_URL")
    waha_api_key: Optional[str] = Field(default=None, env="WAHA_API_KEY")
    waha_session: str = Field(default="default", env="WAHA_SESSION")
    waha_number_primary: str = Field(default="+62 853-19000-230", env="WAHA_NUMBER_PRIMARY")
    waha_number_backup: str = Field(default="+62 853-19000-140", env="WAHA_NUMBER_BACKUP")
    
    # Email WBS
    wbs_email: str = Field(default="wbs@bpkh.go.id", env="WBS_EMAIL")
    
    # Web Portal
    wbs_portal_url: str = Field(default="https://wbs.bpkh.go.id", env="WBS_PORTAL_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# ============================================================================
# CHANNEL PELAPORAN (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
REPORTING_CHANNELS = {
    "WEB": {
        "name": "Web Portal",
        "contact": "wbs.bpkh.go.id",
        "description": "Form online dengan AI analysis"
    },
    "WHATSAPP": {
        "name": "WhatsApp",
        "contact": "+62 853-19000-230",
        "description": "Chat langsung, auto-reply ID tiket"
    },
    "WHATSAPP_BACKUP": {
        "name": "WhatsApp (Cadangan)",
        "contact": "+62 853-19000-140",
        "description": "Nomor cadangan"
    },
    "EMAIL": {
        "name": "Email",
        "contact": "wbs@bpkh.go.id",
        "description": "Pelaporan via email"
    }
}


# ============================================================================
# STAKEHOLDERS (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
STAKEHOLDERS = {
    "PELAPOR": {
        "name": "Pelapor",
        "role": "Melaporkan dugaan pelanggaran",
        "access": ["Web Portal", "WhatsApp", "Email"]
    },
    "UP1": {
        "name": "Pengelola WBS (UP1)",
        "role": "Menindaklanjuti laporan",
        "access": ["Dashboard Admin"]
    },
    "AUDIT_INTERNAL": {
        "name": "Bidang Audit Internal",
        "role": "Menindaklanjuti laporan dengan audit investigasi",
        "access": ["Dashboard AI"]
    },
    "SUPER_ADMIN": {
        "name": "Super Admin",
        "role": "Manajemen sistem & user",
        "access": ["Dashboard Admin (Full)"]
    },
    "PIMPINAN": {
        "name": "Pimpinan",
        "role": "Review hasil investigasi",
        "access": ["Dashboard", "Report"]
    }
}


# ============================================================================
# USER ROLES (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
USER_ROLES = {
    "PELAPOR": {
        "name": "Pelapor",
        "access": ["Web Portal", "WhatsApp"],
        "capabilities": ["Buat laporan", "tracking", "chat"]
    },
    "PENGELOLA": {
        "name": "Pengelola",
        "access": ["Dashboard Admin"],
        "capabilities": ["Kelola laporan", "update", "balas"]
    },
    "SUPER_ADMIN": {
        "name": "Super Admin",
        "access": ["Full Access"],
        "capabilities": ["Semua + user management"]
    }
}


# ============================================================================
# VIOLATION CATEGORIES (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
VIOLATION_CATEGORIES = {
    "KORUPSI": {
        "no": 1,
        "name": "Korupsi",
        "description": "Penyalahgunaan wewenang untuk kepentingan pribadi",
        "legal_basis": ["KUHP Pasal 2", "KUHP Pasal 3", "UU Tipikor (UU 31/1999 jo UU 20/2001)"]
    },
    "GRATIFIKASI": {
        "no": 2,
        "name": "Gratifikasi / Penyuapan",
        "description": "Pemberian hadiah/fasilitas yang berkaitan dengan jabatan",
        "legal_basis": ["UU No. 11 Tahun 1980"]
    },
    "PENGGELAPAN": {
        "no": 3,
        "name": "Penggelapan",
        "description": "Penggelapan aset atau uang",
        "legal_basis": ["KUHP Pasal 372"]
    },
    "PENIPUAN": {
        "no": 4,
        "name": "Penipuan",
        "description": "Tindakan penipuan atau kecurangan",
        "legal_basis": ["KUHP Pasal 378"]
    },
    "PENCURIAN": {
        "no": 5,
        "name": "Pencurian",
        "description": "Pencurian aset atau barang",
        "legal_basis": ["KUHP Pasal 362"]
    },
    "PEMERASAN": {
        "no": 6,
        "name": "Pemerasan",
        "description": "Pemerasan atau ancaman",
        "legal_basis": ["KUHP Pasal 368"]
    },
    "BENTURAN_KEPENTINGAN": {
        "no": 7,
        "name": "Benturan Kepentingan",
        "description": "Conflict of interest dalam pengambilan keputusan",
        "legal_basis": ["UU No. 30/2014"]
    },
    "PELANGGARAN_KEBIJAKAN": {
        "no": 8,
        "name": "Pelanggaran Kebijakan",
        "description": "Pelanggaran SOP dan kebijakan internal",
        "legal_basis": ["SOP Internal BPKH"]
    },
    "TINDAKAN_CURANG": {
        "no": 9,
        "name": "Tindakan Curang",
        "description": "Tindakan tidak jujur atau curang",
        "legal_basis": ["Kode Etik BPKH"]
    }
}


# ============================================================================
# SEVERITY LEVELS (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
SEVERITY_LEVELS = {
    "CRITICAL": {
        "name": "Kritis",
        "criteria": "Kerugian > Rp 1 Miliar, Pejabat tinggi",
        "sla_initial_hours": 4,        # < 4 jam
        "sla_investigation_hours": 24,  # < 24 jam (1 hari)
        "sla_resolution_days": 7,       # < 7 hari
        "priority": "Sangat Tinggi",
        "description": "Pelanggaran sangat serius, melibatkan pejabat tinggi atau kerugian sangat besar"
    },
    "HIGH": {
        "name": "Tinggi",
        "criteria": "Kerugian Rp 100 Juta - 1 Miliar",
        "sla_initial_hours": 24,        # < 24 jam
        "sla_investigation_hours": 72,   # < 3 hari
        "sla_resolution_days": 14,       # < 14 hari
        "priority": "Tinggi",
        "description": "Pelanggaran serius dengan kerugian signifikan"
    },
    "MEDIUM": {
        "name": "Sedang",
        "criteria": "Kerugian Rp 10 - 100 Juta",
        "sla_initial_hours": 72,         # < 3 hari
        "sla_investigation_hours": 168,   # < 7 hari
        "sla_resolution_days": 30,        # < 30 hari
        "priority": "Sedang",
        "description": "Pelanggaran dengan potensi kerugian moderat"
    },
    "LOW": {
        "name": "Rendah",
        "criteria": "Kerugian < Rp 10 Juta",
        "sla_initial_hours": 168,        # < 7 hari
        "sla_investigation_hours": 336,   # < 14 hari
        "sla_resolution_days": 60,        # < 60 hari
        "priority": "Rendah",
        "description": "Pelanggaran minor dengan dampak terbatas"
    }
}


# ============================================================================
# REPORT STATUS (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
REPORT_STATUS = {
    "NEW_WEB": {
        "code": "NEW_WEB",
        "name": "Baru - Via Web",
        "description": "Laporan baru masuk dari portal web"
    },
    "NEW_WHATSAPP": {
        "code": "NEW_WHATSAPP",
        "name": "Baru - Via WhatsApp",
        "description": "Laporan baru masuk dari WhatsApp"
    },
    "NEW_EMAIL": {
        "code": "NEW_EMAIL",
        "name": "Baru - Via Email",
        "description": "Laporan baru masuk dari Email"
    },
    "REVIEWING": {
        "code": "REVIEWING",
        "name": "Sedang Ditinjau",
        "description": "Pengelola sedang mereview laporan"
    },
    "NEED_INFO": {
        "code": "NEED_INFO",
        "name": "Butuh Informasi",
        "description": "Menunggu informasi tambahan dari pelapor"
    },
    "INVESTIGATING": {
        "code": "INVESTIGATING",
        "name": "Dalam Investigasi",
        "description": "Proses investigasi sedang berjalan"
    },
    "ESCALATED": {
        "code": "ESCALATED",
        "name": "Ditingkatkan",
        "description": "Laporan dieskalasi ke level yang lebih tinggi"
    },
    "HOLD": {
        "code": "HOLD",
        "name": "Hold",
        "description": "Laporan ditunda sementara (menunggu kondisi tertentu)"
    },
    "CLOSED_PROVEN": {
        "code": "CLOSED_PROVEN",
        "name": "Selesai - Terbukti",
        "description": "Pelanggaran terbukti, tindak lanjut dilakukan"
    },
    "CLOSED_NOT_PROVEN": {
        "code": "CLOSED_NOT_PROVEN",
        "name": "Selesai - Tidak Terbukti",
        "description": "Bukti tidak cukup, laporan diarsipkan"
    }
}

# Status Lifecycle: BARU → SEDANG DITINJAU → BUTUH INFO (opsional) → DALAM INVESTIGASI → SELESAI
STATUS_LIFECYCLE = {
    "NEW_WEB": ["REVIEWING", "NEED_INFO", "HOLD"],
    "NEW_WHATSAPP": ["REVIEWING", "NEED_INFO", "HOLD"],
    "NEW_EMAIL": ["REVIEWING", "NEED_INFO", "HOLD"],
    "REVIEWING": ["NEED_INFO", "INVESTIGATING", "ESCALATED", "HOLD", "CLOSED_NOT_PROVEN"],
    "NEED_INFO": ["REVIEWING", "INVESTIGATING", "HOLD", "CLOSED_NOT_PROVEN"],
    "INVESTIGATING": ["ESCALATED", "HOLD", "CLOSED_PROVEN", "CLOSED_NOT_PROVEN"],
    "ESCALATED": ["INVESTIGATING", "HOLD", "CLOSED_PROVEN", "CLOSED_NOT_PROVEN"],
    "HOLD": ["REVIEWING", "NEED_INFO", "INVESTIGATING", "CLOSED_NOT_PROVEN"],
    "CLOSED_PROVEN": [],  # Final state
    "CLOSED_NOT_PROVEN": []  # Final state
}


# ============================================================================
# ESCALATION MATRIX (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
ESCALATION_MATRIX = {
    "LEVEL_1": {
        "level": 1,
        "party": "Pengelola WBS",
        "condition": "Penanganan standar"
    },
    "LEVEL_2": {
        "level": 2,
        "party": "Kepala Unit WBS",
        "condition": "SLA breach atau severity Critical"
    },
    "LEVEL_3": {
        "level": 3,
        "party": "Anggota Badan Pelaksana yang membawahi Bidang Kepatuhan",
        "condition": "Melibatkan pejabat eselon atau kerugian > 500 Juta"
    },
    "LEVEL_4": {
        "level": 4,
        "party": "Dewan Pengawas",
        "condition": "Melibatkan Direksi atau kerugian > 1 Miliar"
    }
}


# ============================================================================
# AI MULTI-AGENT ARCHITECTURE (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
AI_AGENTS = {
    "CONTEXT_RETRIEVER": {
        "name": "Context Retriever",
        "function": "Mengambil konteks relevan dari knowledge base (regulasi, SOP, kasus sebelumnya)"
    },
    "SEVERITY_ANALYZER": {
        "name": "Severity Analyzer",
        "function": "Menilai tingkat keparahan laporan (Critical/High/Medium/Low)"
    },
    "FRAUD_DETECTOR": {
        "name": "Fraud Detector",
        "function": "Mendeteksi indikasi fraud berdasarkan pola yang dilaporkan"
    },
    "SIMILAR_FINDER": {
        "name": "Similar Finder",
        "function": "Mencari kasus serupa dari database laporan sebelumnya"
    },
    "COMPLIANCE_CHECKER": {
        "name": "Compliance Checker",
        "function": "Memeriksa kepatuhan terhadap regulasi dan kebijakan"
    },
    "SUMMARY_GENERATOR": {
        "name": "Summary Generator",
        "function": "Merangkum hasil analisis dari semua agent"
    },
    "FINALIZER": {
        "name": "Finalizer",
        "function": "Menghasilkan output final dengan rekomendasi tindakan"
    }
}


# ============================================================================
# FRAUD SCORE INTERPRETATION (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
FRAUD_SCORE_LEVELS = {
    "LOW": {
        "min": 0.00,
        "max": 0.30,
        "label": "Indikasi Rendah",
        "description": "Risiko fraud minimal, perlu monitoring standar"
    },
    "MEDIUM": {
        "min": 0.31,
        "max": 0.70,
        "label": "Indikasi Sedang",
        "description": "Risiko fraud moderat, perlu investigasi lebih lanjut"
    },
    "HIGH": {
        "min": 0.71,
        "max": 1.00,
        "label": "Indikasi Tinggi",
        "description": "Risiko fraud tinggi, prioritas investigasi"
    }
}


# ============================================================================
# PRIORITY MAPPING (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
PRIORITY_MAP = {
    "CRITICAL": {
        "code": "P1",
        "name": "Sangat Tinggi",
        "description": "Immediate action required"
    },
    "HIGH": {
        "code": "P2",
        "name": "Tinggi",
        "description": "Urgent attention needed"
    },
    "MEDIUM": {
        "code": "P3",
        "name": "Sedang",
        "description": "Normal priority"
    },
    "LOW": {
        "code": "P4",
        "name": "Rendah",
        "description": "Low priority"
    }
}


# ============================================================================
# PROCESS STAGES (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
PROCESS_STAGES = {
    1: {
        "stage": "Penerimaan Laporan",
        "activity": "Sistem mencatat laporan dan menghasilkan ID Tiket"
    },
    2: {
        "stage": "Review Awal",
        "activity": "UP1/Pengelola menelaah laporan & hasil analisis AI"
    },
    3: {
        "stage": "Update Status",
        "activity": "Status menjadi Sedang Ditinjau / Butuh Info"
    },
    4: {
        "stage": "Komunikasi",
        "activity": "Klarifikasi dengan pelapor via Web Portal / WhatsApp"
    },
    5: {
        "stage": "Eskalasi Investigasi",
        "activity": "Laporan layak diteruskan ke Bidang Audit Internal"
    },
    6: {
        "stage": "Investigasi",
        "activity": "Audit Internal melakukan investigasi"
    },
    7: {
        "stage": "Keputusan",
        "activity": "Hasil: Terbukti / Tidak Terbukti / Rekomendasi"
    },
    8: {
        "stage": "Notifikasi",
        "activity": "UP1 menyampaikan pokok hasil ke pelapor"
    }
}


# ============================================================================
# SECURITY PRINCIPLES (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
SECURITY_PRINCIPLES = {
    "ANONIMITAS": {
        "principle": "Anonimitas",
        "implementation": "Identitas pelapor dilindungi, nomor WA di-mask"
    },
    "ENKRIPSI": {
        "principle": "Enkripsi",
        "implementation": "HTTPS untuk semua komunikasi, database encrypted at rest"
    },
    "ACCESS_CONTROL": {
        "principle": "Access Control",
        "implementation": "Role-based access (Pelapor, Pengelola, Admin), logging akses"
    },
    "PERLINDUNGAN_PELAPOR": {
        "principle": "Perlindungan Pelapor",
        "implementation": "UU No. 31/2014, non-retaliation policy, kanal confidential"
    }
}


# ============================================================================
# LEGAL REFERENCES (Sesuai Business Process WBS BPKH v1.1)
# ============================================================================
LEGAL_REFERENCES = [
    {
        "name": "Kode Etik BPKH",
        "description": "Kode Etik Pegawai BPKH"
    },
    {
        "name": "SOP Penanganan Pengaduan",
        "description": "Standard Operating Procedure penanganan pengaduan WBS"
    },
    {
        "name": "UU No. 31/2014",
        "description": "Perubahan Atas UU No. 13/2006 tentang Perlindungan Saksi Dan Korban"
    },
    {
        "name": "UU No. 20/2001",
        "description": "Perubahan Atas UU No. 31/1999 tentang Pemberantasan Tindak Pidana Korupsi"
    },
    {
        "name": "PKBP 8/2022",
        "description": "Tata Cara Pengelolaan Dan Tindak Lanjut Pelaporan Pelanggaran (Whistleblowing) Di Lingkungan BPKH"
    },
    {
        "name": "PKBP 13/2024",
        "description": "Pedoman Audit Khusus Badan Pengelola Keuangan Haji"
    }
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_fraud_score_level(score: float) -> Dict[str, Any]:
    """Get fraud score interpretation based on score value"""
    if score <= 0.30:
        return FRAUD_SCORE_LEVELS["LOW"]
    elif score <= 0.70:
        return FRAUD_SCORE_LEVELS["MEDIUM"]
    else:
        return FRAUD_SCORE_LEVELS["HIGH"]


def get_severity_sla(severity: str) -> Dict[str, Any]:
    """Get SLA details for a given severity level"""
    return SEVERITY_LEVELS.get(severity.upper(), SEVERITY_LEVELS["MEDIUM"])


def get_allowed_status_transitions(current_status: str) -> List[str]:
    """Get allowed status transitions from current status"""
    return STATUS_LIFECYCLE.get(current_status, [])


def get_escalation_level(severity: str, loss_amount: float = 0, involves_director: bool = False) -> Dict[str, Any]:
    """Determine escalation level based on severity and conditions"""
    if involves_director or loss_amount > 1_000_000_000:
        return ESCALATION_MATRIX["LEVEL_4"]
    elif loss_amount > 500_000_000:
        return ESCALATION_MATRIX["LEVEL_3"]
    elif severity.upper() == "CRITICAL":
        return ESCALATION_MATRIX["LEVEL_2"]
    else:
        return ESCALATION_MATRIX["LEVEL_1"]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings
settings = get_settings()
