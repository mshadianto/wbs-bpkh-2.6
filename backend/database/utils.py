"""
WBS BPKH AI - Database Utilities
================================
Shared sanitization, validation, and parsing helpers.
"""

import re
import html
from typing import List, Optional
from datetime import datetime
from loguru import logger


MAX_FIELD_LENGTHS = {
    "title": 500,
    "description": 50000,
    "content": 50000,
    "incident_location": 500,
    "reporter_email": 255,
    "reporter_name": 255,
    "reporter_phone": 50,
}


def validate_field_length(value: str, field_name: str, max_length: int = 0) -> str:
    """Truncate field if it exceeds max length to prevent resource exhaustion."""
    if not value:
        return value
    limit = max_length or MAX_FIELD_LENGTHS.get(field_name, 10000)
    return value[:limit]


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if not text:
        return text
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(
        r'<(iframe|object|embed|link|style|img\s+[^>]*onerror)[^>]*>.*?</\1>',
        '', text, flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    text = html.escape(text)
    return text


def sanitize_list(items: List[str]) -> List[str]:
    """Sanitize a list of strings."""
    if not items:
        return items
    return [sanitize_input(item) for item in items]


def sanitize_search_query(search: str) -> str:
    """Sanitize search query for use in PostgREST ilike filters."""
    if not search:
        return search
    sanitized = re.sub(r'[,.()\[\]{}\\;\'"]', '', search)
    return sanitized[:200].strip()


def parse_date_safe(date_str: str) -> Optional[str]:
    """Safely parse date string to ISO format. Returns None if invalid."""
    if not date_str or date_str in ["Unknown", "Tidak disebutkan", "N/A", "-"]:
        return None

    date_str = str(date_str).strip()

    for fmt in ["%Y-%m-%d", "%Y-%m"]:
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            pass

    if re.match(r"^\d{4}$", date_str):
        try:
            year = int(date_str)
            if 1900 <= year <= 2100:
                return f"{year}-01-01"
        except ValueError:
            pass

    for fmt in ["%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            pass

    logger.warning(f"Could not parse date: {date_str}")
    return None
