import logging
from typing import Optional
from supabase import Client, create_client
from backend.app.config import get_settings

logger = logging.getLogger("aegismesh.db")

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Initializes and returns a singleton Supabase client if credentials are configured.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    settings = get_settings()
    if not settings.has_supabase:
        logger.info("Supabase credentials not configured. Running with in-memory repository.")
        return None

    try:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        _supabase_client = create_client(settings.SUPABASE_URL, key)
        logger.info("Supabase client initialized successfully.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def check_supabase_connection() -> dict:
    """
    Checks live Supabase connection status.
    """
    client = get_supabase_client()
    if not client:
        return {
            "connected": False,
            "error": "Supabase credentials not configured in environment (.env)"
        }

    try:
        # Ping Supabase by checking agents table
        res = client.table("agents").select("id").limit(1).execute()
        return {
            "connected": True,
            "status": "ready",
            "message": "Connected to Supabase PostgreSQL database."
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }
