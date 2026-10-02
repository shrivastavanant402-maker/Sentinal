import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.db.repositories.contracts import get_contract_repository
from backend.app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    MissionContract,
)

logger = logging.getLogger("aegismesh.api.contracts")

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("/{agent_id}", response_model=MissionContract)
async def get_contract(
    agent_id: str,
    mission_id: Optional[str] = Query(None, description="Optional mission context ID"),
) -> MissionContract:
    """
    Retrieves the active mission contract for an agent.
    If mission_id is provided, looks up contract matching agent + mission.
    """
    repo = get_contract_repository()
    contract = await repo.get_contract_for_agent(agent_id=agent_id, mission_id=mission_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active mission contract found for agent '{agent_id}'",
        )
    return contract


@router.put("/{agent_id}", response_model=MissionContract)
async def update_or_create_contract(
    agent_id: str,
    contract_data: ContractCreate,
    mission_id: Optional[str] = Query(None, description="Optional mission context ID"),
) -> MissionContract:
    """
    Updates or creates the active mission contract for an agent.
    """
    repo = get_contract_repository()
    mid = mission_id or contract_data.mission_id

    existing = await repo.get_contract_for_agent(agent_id=agent_id, mission_id=mid)
    if existing:
        update_model = ContractUpdate(
            name=contract_data.name,
            description=contract_data.description,
            allowed_tools=contract_data.allowed_tools,
            forbidden_tools=contract_data.forbidden_tools,
            allowed_resources=contract_data.allowed_resources,
            risk_level=contract_data.risk_level,
            enabled=contract_data.enabled,
        )
        updated = await repo.update_contract(
            agent_id=agent_id, update=update_model, mission_id=mid
        )
        if updated:
            return updated

    # Otherwise create
    if contract_data.agent_id != agent_id:
        contract_data.agent_id = agent_id
    contract_data.mission_id = mid
    return await repo.create_contract(contract_data)


@router.get("", response_model=List[MissionContract])
async def list_all_contracts() -> List[MissionContract]:
    """Lists all mission contracts."""
    repo = get_contract_repository()
    return await repo.list_contracts()
