from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.api.health import router as health_router
from backend.app.api.agents import router as agents_router
from backend.app.api.events import router as events_router
from backend.app.api.ledger import router as ledger_router
from backend.app.api.alerts import router as alerts_router
from backend.app.api.enforcement import router as enforcement_router
from backend.app.api.contracts import router as contracts_router
from backend.app.api.trust import router as trust_router
from backend.app.api.attacks import router as attacks_router
from backend.app.api.anomalies import router as anomalies_router
from backend.app.db.repository import get_repository
from backend.app.db.repositories.contracts import get_contract_repository, get_default_seed_contracts
from backend.app.schemas.agent import AgentCreate
from backend.app.schemas.contract import ContractCreate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aegismesh")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup & shutdown hooks:
    - Auto-registers initial foundational agents (Planner, Researcher, Executor)
    - Verifies repository readiness
    """
    logger.info("Initializing AegisMesh Runtime Integrity System...")
    repo = get_repository()

    # Pre-register foundational demo agents if not existing
    default_agents = [
        AgentCreate(
            id="planner-01",
            name="Planner Agent",
            role="planner",
            capabilities=["plan.declare", "task.delegate", "objective.decompose"],
            metadata={"description": "Strategic planning and task decomposition agent"}
        ),
        AgentCreate(
            id="researcher-01",
            name="Researcher Agent",
            role="researcher",
            capabilities=["web.search", "web.read", "research_db.read"],
            metadata={"description": "External information retrieval and evidence gathering agent"}
        ),
        AgentCreate(
            id="executor-01",
            name="Executor Agent",
            role="executor",
            capabilities=["report.generate", "fs.read", "fs.write"],
            metadata={"description": "Artifact synthesis and action execution agent"}
        )
    ]

    for agent_data in default_agents:
        existing = await repo.get_agent(agent_data.id)
        if not existing:
            await repo.register_agent(agent_data)
            logger.info(f"Registered foundation agent: {agent_data.id} ({agent_data.role})")

    # Seed default mission contracts for foundation agents if not existing
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
                logger.info(f"Seeded default mission contract for agent: {seed_c.agent_id}")
            except Exception as exc:
                logger.warning(f"Could not seed contract for {seed_c.agent_id}: {exc}")

    logger.info("AegisMesh Runtime Integrity Core is ready.")
    yield
    logger.info("Shutting down AegisMesh Core.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AegisMesh Autonomous Agent Runtime Integrity System",
        description="Runtime security, mission integrity, and verifiable evidence ledger for multi-agent systems.",
        version="0.1.0",
        lifespan=lifespan
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount endpoints directly for root access
    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(events_router)
    app.include_router(ledger_router)
    app.include_router(alerts_router)
    app.include_router(enforcement_router)
    app.include_router(contracts_router)
    app.include_router(trust_router)
    app.include_router(attacks_router)
    app.include_router(anomalies_router)

    # Also mount under /api/v1 for standard API versioning
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(ledger_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(enforcement_router, prefix="/api/v1")
    app.include_router(contracts_router, prefix="/api/v1")
    app.include_router(trust_router, prefix="/api/v1")
    app.include_router(attacks_router, prefix="/api/v1")
    app.include_router(anomalies_router, prefix="/api/v1")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("backend.app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
