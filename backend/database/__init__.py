"""
WBS BPKH AI - Database Package
==============================
Modular database repositories with shared Supabase client.
"""

from .client import SupabaseDB
from .utils import (
    sanitize_input, sanitize_list, sanitize_search_query,
    validate_field_length, parse_date_safe,
    MAX_FIELD_LENGTHS,
)
from .reports import ReportRepository
from .messages import MessageRepository
from .vectors import VectorRepository
from .users import UserRepository, SessionRepository

# Singleton repository instances (same public API as before)
report_repo = ReportRepository()
message_repo = MessageRepository()
vector_repo = VectorRepository()
user_repo = UserRepository()
session_repo = SessionRepository()

__all__ = [
    "SupabaseDB",
    "sanitize_input", "sanitize_list", "sanitize_search_query",
    "validate_field_length", "parse_date_safe", "MAX_FIELD_LENGTHS",
    "ReportRepository", "MessageRepository", "VectorRepository",
    "UserRepository", "SessionRepository",
    "report_repo", "message_repo", "vector_repo",
    "user_repo", "session_repo",
]
