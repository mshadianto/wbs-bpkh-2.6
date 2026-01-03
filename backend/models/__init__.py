"""
WBS BPKH AI - Pydantic Models
=============================
Data models for API requests and responses.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============== Enums ==============

class ReportChannel(str, Enum):
    WEB = "WEB"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class ReportStatus(str, Enum):
    NEW = "NEW"
    REVIEWING = "REVIEWING"
    NEED_INFO = "NEED_INFO"
    INVESTIGATING = "INVESTIGATING"
    HOLD = "HOLD"
    ESCALATED = "ESCALATED"
    CLOSED_PROVEN = "CLOSED_PROVEN"
    CLOSED_NOT_PROVEN = "CLOSED_NOT_PROVEN"
    CLOSED_INVALID = "CLOSED_INVALID"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ViolationCategory(str, Enum):
    FRAUD = "FRAUD"
    CORRUPTION = "CORRUPTION"
    GRATIFICATION = "GRATIFICATION"
    COI = "COI"
    PROCUREMENT = "PROCUREMENT"
    DATA_BREACH = "DATA_BREACH"
    ETHICS = "ETHICS"
    MISCONDUCT = "MISCONDUCT"
    OTHER = "OTHER"


class SenderType(str, Enum):
    REPORTER = "REPORTER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


# ============== Report Models ==============

class ReportCreate(BaseModel):
    """Model for creating new report"""
    channel: ReportChannel = ReportChannel.WEB
    reporter_contact: Optional[str] = Field(
        None, 
        description="Contact info (email/phone) - optional for anonymous"
    )
    is_anonymous: bool = Field(
        True, 
        description="Whether reporter wants to remain anonymous"
    )
    subject: str = Field(
        ..., 
        min_length=10, 
        max_length=200,
        description="Brief subject/title of report"
    )
    description: str = Field(
        ..., 
        min_length=50,
        description="Detailed description of violation"
    )
    incident_date: Optional[str] = Field(
        None, 
        description="Date of incident (YYYY-MM-DD or description)"
    )
    incident_location: Optional[str] = Field(
        None, 
        description="Location of incident"
    )
    parties_involved: List[str] = Field(
        default_factory=list,
        description="Names/positions of parties involved"
    )
    attachments: List[str] = Field(
        default_factory=list,
        description="List of attachment file IDs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "channel": "WEB",
                "is_anonymous": True,
                "subject": "Dugaan pengadaan barang tidak sesuai prosedur",
                "description": "Saya melaporkan adanya dugaan penyimpangan dalam pengadaan barang di unit XYZ. Proses tender dilakukan tanpa pengumuman yang memadai...",
                "incident_date": "2024-12",
                "incident_location": "Kantor Pusat BPKH",
                "parties_involved": ["Kepala Bagian Pengadaan", "Vendor ABC"]
            }
        }


class ReportResponse(BaseModel):
    """Model for report response"""
    id: str
    ticket_id: str
    channel: str
    status: str
    subject: Optional[str] = Field(None, alias="title")
    description: str
    severity: Optional[str] = None
    category: Optional[str] = None
    fraud_score: Optional[float] = None
    is_anonymous: bool = False
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
        populate_by_name = True


class ReportDetail(ReportResponse):
    """Detailed report model with analysis"""
    ai_analysis: Optional[Dict[str, Any]] = None
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None
    parties_involved: List[str] = []
    messages_count: int = 0


class ReportListResponse(BaseModel):
    """Response for report list"""
    total: int
    reports: List[ReportResponse]
    page: int
    per_page: int


# ============== Message Models ==============

class MessageCreate(BaseModel):
    """Model for creating new message"""
    content: str = Field(
        ..., 
        min_length=1,
        description="Message content"
    )
    attachments: List[str] = Field(
        default_factory=list,
        description="Attachment file IDs"
    )


class MessageResponse(BaseModel):
    """Model for message response"""
    id: str
    report_id: str
    content: str
    sender_type: str
    attachments: List[str] = []
    is_read: bool
    created_at: str
    
    class Config:
        from_attributes = True


# ============== Analysis Models ==============

class AnalysisRequest(BaseModel):
    """Model for analysis request"""
    report_id: str
    use_full_analysis: bool = Field(
        True,
        description="Use full multi-agent analysis or quick analysis"
    )


class IntakeResult(BaseModel):
    """Result from Intake Agent"""
    what: Dict[str, Any]
    who: Dict[str, Any]
    when: Dict[str, Any]
    where: Dict[str, Any]
    how: Dict[str, Any]
    completeness_score: float
    missing_elements: List[str] = []


class FraudAnalysisResult(BaseModel):
    """Result from Analysis Agent"""
    fraud_score: float = Field(..., ge=0, le=1)
    red_flags_identified: List[Dict[str, Any]] = []
    fraud_triangle: Dict[str, Any] = {}
    estimated_financial_impact: Dict[str, Any] = {}
    confidence_level: str


class ComplianceResult(BaseModel):
    """Result from Compliance Agent"""
    categories: List[str]
    potential_violations: List[Dict[str, Any]]
    compliance_status: Dict[str, Any]
    legal_implications: Dict[str, Any]


class SeverityResult(BaseModel):
    """Result from Severity Agent"""
    level: SeverityLevel
    score: int = Field(..., ge=0, le=100)
    factors: Dict[str, Any]
    sla: Dict[str, int]
    escalation_required: bool = False


class RecommendationResult(BaseModel):
    """Result from Recommendation Agent"""
    immediate_actions: List[Dict[str, Any]]
    short_term_actions: List[Dict[str, Any]]
    investigation_requirements: Dict[str, Any]
    overall_recommendation: str


class SummaryResult(BaseModel):
    """Result from Summary Agent"""
    title: str
    executive_summary: str
    key_findings: List[str]
    risk_assessment: Dict[str, Any]
    recommended_action: Dict[str, Any]


class FullAnalysisResponse(BaseModel):
    """Complete analysis response"""
    analysis_id: str
    analyzed_at: str
    status: str
    
    # Core metrics
    severity: Optional[str] = None
    category: Optional[str] = None
    fraud_score: Optional[float] = None
    priority: Optional[str] = None
    
    # Agent results
    intake: Optional[Dict[str, Any]] = None
    fraud_analysis: Optional[Dict[str, Any]] = None
    compliance: Optional[Dict[str, Any]] = None
    severity_details: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    executive_summary: Optional[Dict[str, Any]] = None
    
    # Metadata
    similar_cases: List[Dict[str, Any]] = []
    agents_used: List[str] = []


# ============== Dashboard Models ==============

class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_reports: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    pending_review: int
    sla_at_risk: int


class StatusUpdate(BaseModel):
    """Status update request"""
    new_status: ReportStatus
    notes: Optional[str] = None


# ============== Ticket Models ==============

class TicketLookup(BaseModel):
    """Ticket lookup request"""
    ticket_id: str = Field(
        ..., 
        min_length=8, 
        max_length=8,
        description="8-character ticket ID"
    )


class TicketStatusResponse(BaseModel):
    """Public ticket status response (for whistleblowers)"""
    ticket_id: str
    status: str
    status_description: str
    last_updated: str
    can_add_info: bool = True
