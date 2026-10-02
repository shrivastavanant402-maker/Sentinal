from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.db.repository import get_repository
from backend.app.schemas.event import EventCreate, EventResponse
from backend.app.schemas.agent import AgentCreate

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(event_data: EventCreate):
    repo = get_repository()

    # Verify agent exists or auto-register standard agent
    agent = await repo.get_agent(event_data.agent_id)
    if not agent:
        # Auto-register agent with default info if first time seen
        role = event_data.agent_id.split("-")[0] if "-" in event_data.agent_id else "agent"
        await repo.register_agent(
            AgentCreate(
                id=event_data.agent_id,
                name=event_data.agent_id.replace("-", " ").title(),
                role=role
            )
        )

    event_response = await repo.store_event(event_data)
    return event_response


@router.get("", response_model=List[EventResponse])
async def list_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    repo = get_repository()
    return await repo.list_events(limit=limit, offset=offset)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str):
    repo = get_repository()
    event = await repo.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found"
        )
    return event
