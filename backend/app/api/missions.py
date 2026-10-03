import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request

from agents.common.client import AegisMeshClient
from agents.orchestrator.runner import MissionCoordinator
from backend.app.db.repository import get_repository
from backend.app.db.repositories.contracts import (
    get_contract_repository,
    get_default_seed_contracts,
)
from backend.app.schemas.agent import AgentCreate
from backend.app.schemas.contract import ContractCreate
from backend.app.schemas.mission import MissionRunRequest, MissionRunResponse

logger = logging.getLogger("aegismesh.api.missions")

router = APIRouter(prefix="/missions", tags=["Missions"])


async def ensure_foundational_agents() -> None:
    """Ensure foundational agents and default contracts exist in repository."""
    repo = get_repository()
    default_agents = [
        AgentCreate(
            id="planner-01",
            name="Planner Agent",
            role="planner",
            capabilities=["plan.declare", "task.delegate", "objective.decompose"],
            metadata={"description": "Strategic planning and task decomposition agent"},
        ),
        AgentCreate(
            id="researcher-01",
            name="Researcher Agent",
            role="researcher",
            capabilities=["web.search", "web.read", "research_db.read"],
            metadata={"description": "External information retrieval and evidence gathering agent"},
        ),
        AgentCreate(
            id="executor-01",
            name="Executor Agent",
            role="executor",
            capabilities=["report.generate", "fs.read", "fs.write"],
            metadata={"description": "Artifact synthesis and action execution agent"},
        ),
        AgentCreate(
            id="ide-agent-01",
            name="VS Code IDE Sentinel",
            role="ide_sentinel",
            capabilities=["shell.exec", "fs.read", "fs.write", "code.analyze"],
            metadata={"description": "VS Code developer assistant and workspace execution sentinel"},
        ),
    ]
    for agent_data in default_agents:
        existing = await repo.get_agent(agent_data.id)
        if not existing:
            await repo.register_agent(agent_data)

    contract_repo = get_contract_repository()
    for seed_c in get_default_seed_contracts():
        existing_contract = await contract_repo.get_contract_for_agent(seed_c.agent_id)
        if not existing_contract:
            try:
                await contract_repo.create_contract(
                    ContractCreate(
                        id=seed_c.id,
                        mission_id=seed_c.mission_id,
                        agent_id=seed_c.agent_id,
                        name=seed_c.name,
                        description=seed_c.description,
                        allowed_tools=seed_c.allowed_tools,
                        forbidden_tools=seed_c.forbidden_tools,
                        allowed_resources=seed_c.allowed_resources,
                        risk_level=seed_c.risk_level,
                        enabled=seed_c.enabled,
                    )
                )
            except Exception:
                pass


def get_mission_coordinator(request: Request) -> MissionCoordinator:
    """
    Dependency provider for MissionCoordinator bound to current FastAPI application
    via ASGI client transport.
    """
    client = AegisMeshClient(app=request.app)
    return MissionCoordinator(client=client)


@router.post("/run", response_model=MissionRunResponse)
async def run_mission(
    payload: MissionRunRequest,
    coordinator: MissionCoordinator = Depends(get_mission_coordinator),
) -> MissionRunResponse:
    """
    Executes a multi-agent mission under AegisMesh runtime integrity enforcement:
    Planner -> Researcher -> Executor
    Guarded at every step by /enforce policy and logged to the Evidence Ledger.
    """
    logger.info("Received mission run request with goal: %s", payload.goal)
    await ensure_foundational_agents()

    result = await coordinator.run_mission(
        goal=payload.goal,
        mission_id=payload.mission_id,
        session_id=payload.session_id,
        raise_on_failure=False,
    )

    logger.info(
        "Mission [%s] completed with status [%s], %d event IDs",
        result.mission_id,
        result.status,
        len(result.event_ids),
    )
    return MissionRunResponse(**result.model_dump())
