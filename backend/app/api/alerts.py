from typing import List
from fastapi import APIRouter, Query, status
from backend.app.db.repository import get_repository
from backend.app.schemas.alert import AlertCreate, AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(alert_data: AlertCreate):
    repo = get_repository()
    return await repo.store_alert(alert_data)


@router.get("", response_model=List[AlertResponse])
async def list_alerts(limit: int = Query(100, ge=1, le=1000)):
    repo = get_repository()
    return await repo.list_alerts(limit=limit)
