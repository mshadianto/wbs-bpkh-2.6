"""
WBS BPKH AI - Database Client
==============================
Supabase singleton client.
"""

from typing import Optional
from supabase import create_client, Client

from config import settings


class SupabaseDB:
    """Supabase Database Client (Singleton)."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase service-role client."""
        if cls._instance is None:
            if not settings.supabase_url or not settings.supabase_service_key:
                raise ValueError("Supabase credentials not configured")
            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )
        return cls._instance

    @classmethod
    def get_anon_client(cls) -> Client:
        """Get anonymous client for public operations."""
        return create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
