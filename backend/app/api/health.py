from datetime import datetime, timezone
from fastapi import APIRouter
from backend.app.config import get_settings
from backend.app.db.client import check_supabase_connection

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    settings = get_settings()
    supabase_status = check_supabase_connection()
    return {
        "status": "healthy",
        "service": "AegisMesh Runtime Integrity Core",
        "environment": settings.AEGISMESH_ENV,
        "supabase": supabase_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
