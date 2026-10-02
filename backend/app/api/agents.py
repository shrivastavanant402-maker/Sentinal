from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.app.db.repository import get_repository
from backend.app.schemas.agent import AgentCreate, AgentResponse, AgentStatus

router = APIRouter(prefix="/agents", tags=["Agents"])


class AgentStatusUpdate(BaseModel):
    status: AgentStatus


@router.post("/register", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(agent_data: AgentCreate):
    repo = get_repository()
    created = await repo.register_agent(agent_data)
    return created


@router.get("", response_model=List[AgentResponse])
async def list_agents():
    repo = get_repository()
    return await repo.list_agents()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    repo = get_repository()
    agent = await repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    return agent


@router.patch("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(agent_id: str, update: AgentStatusUpdate):
    repo = get_repository()
    agent = await repo.update_agent_status(agent_id, update.status)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    return agent
