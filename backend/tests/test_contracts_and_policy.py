from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from backend.app.contracts.validator import (
    ContractOutcome,
    ContractValidationResult,
    MissionContractValidator,
)
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    get_contract_repository,
    set_contract_repository,
)
from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.main import app
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.policy.evaluator import PolicyEvaluationResult, RuntimePolicyEvaluator
from backend.app.policy.risk import classify_action_risk
from backend.app.schemas.agent import AgentCreate, AgentResponse, AgentStatus
from backend.app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    MissionContract,
)
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionReason,
    DecisionResponse,
    DecisionStatus,
    RiskLevel,
)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Initializes clean in-memory repositories and PDP for each test."""
    repo = InMemoryRepository()
    set_repository(repo)
    contract_repo = InMemoryContractRepository(seed=True)
    set_contract_repository(contract_repo)
    set_pdp(PolicyDecisionPoint(contract_repository=contract_repo))


# ---------------------------------------------------------------------------
# 1. Contract Schema Tests
# ---------------------------------------------------------------------------

def test_contract_schema_valid_accepted():
    """1. Valid contract model is parsed and accepted."""
    contract = MissionContract(
        id="contract-test-01",
        mission_id="mission-alpha",
        agent_id="researcher-01",
        name="Alpha Research Contract",
        description="Testing validation",
        allowed_tools=["web.search", "web.read"],
        forbidden_tools=["database.export"],
        allowed_resources=["https://*"],
        risk_level=RiskLevel.LOW,
        enabled=True,
    )
    assert contract.id == "contract-test-01"
    assert contract.agent_id == "researcher-01"
    assert "web.search" in contract.allowed_tools
    assert "database.export" in contract.forbidden_tools
    assert contract.risk_level == RiskLevel.LOW
    assert contract.enabled is True


def test_contract_schema_invalid_rejected():
    """2. Invalid contract model missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        # Missing required agent_id and name
        MissionContract(id="contract-incomplete")


# ---------------------------------------------------------------------------
# 2. Contract Evaluation Tests
# ---------------------------------------------------------------------------

def test_contract_evaluator_allowed_action():
    """3. Explicitly allowed action produces ALLOW outcome."""
    validator = MissionContractValidator()
    contract = MissionContract(
        id="c-1",
        agent_id="researcher-01",
        name="Researcher",
        allowed_tools=["web.search", "web.read"],
        forbidden_tools=["database.export"],
    )
    req = ActionRequest(agent_id="researcher-01", action="web.search")
    result = validator.validate(req, contract)

    assert result.outcome == ContractOutcome.ALLOW
    assert "permitted" in result.reason.lower()


def test_contract_evaluator_forbidden_action():
    """4. Action in forbidden_tools produces DENY outcome."""
    validator = MissionContractValidator()
    contract = MissionContract(
        id="c-1",
        agent_id="researcher-01",
        name="Researcher",
        allowed_tools=["web.search"],
        forbidden_tools=["database.export"],
    )
    req = ActionRequest(agent_id="researcher-01", action="database.export")
    result = validator.validate(req, contract)

    assert result.outcome == ContractOutcome.DENY
    assert "forbidden" in result.reason.lower()


def test_contract_evaluator_action_absent_from_allowlist():
    """5. Action absent from allowed_tools produces DENY outcome."""
    validator = MissionContractValidator()
    contract = MissionContract(
        id="c-1",
        agent_id="researcher-01",
        name="Researcher",
        allowed_tools=["web.search"],
        forbidden_tools=[],
    )
    req = ActionRequest(agent_id="researcher-01", action="random.action")
    result = validator.validate(req, contract)

    assert result.outcome == ContractOutcome.DENY
    assert "not in allowed_tools" in result.reason.lower()


def test_contract_evaluator_disabled_contract():
    """6. Disabled contract produces DENY outcome."""
    validator = MissionContractValidator()
    contract = MissionContract(
        id="c-disabled",
        agent_id="researcher-01",
        name="Disabled Contract",
        allowed_tools=["web.search"],
        enabled=False,
    )
    req = ActionRequest(agent_id="researcher-01", action="web.search")
    result = validator.validate(req, contract)

    assert result.outcome == ContractOutcome.DENY
    assert "disabled" in result.reason.lower()


def test_contract_evaluator_missing_contract():
    """7. Missing contract produces NO_CONTRACT outcome."""
    validator = MissionContractValidator()
    req = ActionRequest(agent_id="uncontracted-01", action="web.search")
    result = validator.validate(req, contract=None)

    assert result.outcome == ContractOutcome.NO_CONTRACT
    assert "no active mission contract" in result.reason.lower()


# ---------------------------------------------------------------------------
# 3. Policy Engine Tests
# ---------------------------------------------------------------------------

def test_policy_engine_researcher_web_search_allows():
    """8. Policy Engine: researcher + web.search -> ALLOW."""
    evaluator = RuntimePolicyEvaluator()
    contract_repo = InMemoryContractRepository(seed=True)
    import asyncio
    contract = asyncio.run(contract_repo.get_contract_for_agent("researcher-01"))
    agent = AgentResponse(
        id="researcher-01",
        name="Deep Researcher",
        role="researcher",
        status=AgentStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    req = ActionRequest(agent_id="researcher-01", action="web.search")
    result = evaluator.evaluate(request=req, agent=agent, contract=contract)

    assert result.allowed is True
    assert result.status == DecisionStatus.ALLOW
    assert result.reason == DecisionReason.ALLOWED_BY_POLICY


def test_policy_engine_researcher_database_export_blocks():
    """9. Policy Engine: researcher + database.export -> BLOCK."""
    evaluator = RuntimePolicyEvaluator()
    contract_repo = InMemoryContractRepository(seed=True)
    import asyncio
    contract = asyncio.run(contract_repo.get_contract_for_agent("researcher-01"))
    agent = AgentResponse(
        id="researcher-01",
        name="Deep Researcher",
        role="researcher",
        status=AgentStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    req = ActionRequest(agent_id="researcher-01", action="database.export")
    result = evaluator.evaluate(request=req, agent=agent, contract=contract)

    assert result.allowed is False
    assert result.status == DecisionStatus.BLOCK
    assert result.risk_level == RiskLevel.HIGH


def test_policy_engine_executor_report_generate_allows():
    """10. Policy Engine: executor + report.generate -> ALLOW."""
    evaluator = RuntimePolicyEvaluator()
    contract_repo = InMemoryContractRepository(seed=True)
    import asyncio
    contract = asyncio.run(contract_repo.get_contract_for_agent("executor-01"))
    agent = AgentResponse(
        id="executor-01",
        name="Task Executor",
        role="executor",
        status=AgentStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    req = ActionRequest(agent_id="executor-01", action="report.generate")
    result = evaluator.evaluate(request=req, agent=agent, contract=contract)

    assert result.allowed is True
    assert result.status == DecisionStatus.ALLOW


def test_policy_engine_executor_shell_exec_blocks():
    """11. Policy Engine: executor + shell.exec -> BLOCK."""
    evaluator = RuntimePolicyEvaluator()
    contract_repo = InMemoryContractRepository(seed=True)
    import asyncio
    contract = asyncio.run(contract_repo.get_contract_for_agent("executor-01"))
    agent = AgentResponse(
        id="executor-01",
        name="Task Executor",
        role="executor",
        status=AgentStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    req = ActionRequest(agent_id="executor-01", action="shell.exec")
    result = evaluator.evaluate(request=req, agent=agent, contract=contract)

    assert result.allowed is False
    assert result.status == DecisionStatus.BLOCK
    assert result.risk_level == RiskLevel.HIGH


def test_policy_engine_planner_task_delegate_allows():
    """12. Policy Engine: planner + task.delegate -> ALLOW."""
    evaluator = RuntimePolicyEvaluator()
    contract_repo = InMemoryContractRepository(seed=True)
    import asyncio
    contract = asyncio.run(contract_repo.get_contract_for_agent("planner-01"))
    agent = AgentResponse(
        id="planner-01",
        name="Lead Planner",
        role="planner",
        status=AgentStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    req = ActionRequest(agent_id="planner-01", action="task.delegate")
    result = evaluator.evaluate(request=req, agent=agent, contract=contract)

    assert result.allowed is True
    assert result.status == DecisionStatus.ALLOW


# ---------------------------------------------------------------------------
# 4. PEP Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pep_uses_mission_contract():
    """13. PEP consults contract repository and enforces contract bounds."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a custom agent
        await client.post("/agents/register", json={
            "id": "analyst-01",
            "name": "Market Analyst",
            "role": "analyst",
        })

        # Set custom contract authorizing ONLY stats.compute
        await client.put("/contracts/analyst-01", json={
            "agent_id": "analyst-01",
            "name": "Analyst Contract",
            "allowed_tools": ["stats.compute"],
            "forbidden_tools": ["web.search"],
        })

        # Allowed tool according to contract
        r1 = await client.post("/enforce", json={
            "agent_id": "analyst-01",
            "action": "stats.compute",
            "payload": {},
        })
        d1 = r1.json()
        assert d1["decision"] == "ALLOW"
        assert d1["allowed"] is True

        # Forbidden tool according to contract
        r2 = await client.post("/enforce", json={
            "agent_id": "analyst-01",
            "action": "web.search",
            "payload": {},
        })
        d2 = r2.json()
        assert d2["decision"] == "BLOCK"
        assert d2["allowed"] is False


@pytest.mark.asyncio
async def test_pep_uses_policy_engine_mission_id():
    """14. PEP respects specific mission_id when provided in ActionRequest."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/agents/register", json={
            "id": "researcher-mission-test",
            "name": "Researcher",
            "role": "researcher",
        })

        # Create contract for mission-restricted
        await client.put("/contracts/researcher-mission-test?mission_id=mission-restricted", json={
            "agent_id": "researcher-mission-test",
            "mission_id": "mission-restricted",
            "name": "Restricted Mission Contract",
            "allowed_tools": ["internal.docs.read"],
            "forbidden_tools": ["web.search"],
        })

        # Request under mission-restricted where web.search is forbidden
        resp = await client.post("/enforce", json={
            "agent_id": "researcher-mission-test",
            "mission_id": "mission-restricted",
            "action": "web.search",
            "payload": {},
        })
        data = resp.json()
        assert data["decision"] == "BLOCK"
        assert data["allowed"] is False


@pytest.mark.asyncio
async def test_blocked_action_never_becomes_allow():
    """15. Blocked action is definitively rejected and never returns allowed=True."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/agents/register", json={
            "id": "researcher-01",
            "name": "Deep Researcher",
            "role": "researcher",
        })

        resp = await client.post("/enforce", json={
            "agent_id": "researcher-01",
            "action": "database.export",
            "payload": {},
        })
        data = resp.json()
        assert data["allowed"] is False
        assert data["decision"] == "BLOCK"


@pytest.mark.asyncio
async def test_existing_quarantine_behavior_preserved():
    """16. Quarantined agent is rejected with QUARANTINE regardless of contract."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/agents/register", json={
            "id": "bad-agent-02",
            "name": "Bad Agent",
            "role": "researcher",
        })
        await client.patch("/agents/bad-agent-02/status", json={"status": "quarantined"})

        resp = await client.post("/enforce", json={
            "agent_id": "bad-agent-02",
            "action": "web.search",
            "payload": {},
        })
        data = resp.json()
        assert data["decision"] == "QUARANTINE"
        assert data["allowed"] is False


@pytest.mark.asyncio
async def test_unknown_agent_remains_blocked():
    """17. Unregistered agent calling /enforce receives BLOCK with INVALID_IDENTITY."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/enforce", json={
            "agent_id": "nonexistent-agent-99",
            "action": "web.search",
            "payload": {},
        })
        data = resp.json()
        assert data["decision"] == "BLOCK"
        assert data["allowed"] is False
        assert "INVALID_IDENTITY" in data["reason"]


# ---------------------------------------------------------------------------
# 5. Contract API Endpoints Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_contract_works():
    """18. GET /contracts/{agent_id} returns active contract."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/contracts/researcher-01")
        assert resp.status_code == 200
        contract = resp.json()
        assert contract["agent_id"] == "researcher-01"
        assert "web.search" in contract["allowed_tools"]


@pytest.mark.asyncio
async def test_put_contract_works():
    """19. PUT /contracts/{agent_id} updates or registers a contract."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/contracts/custom-worker-01", json={
            "agent_id": "custom-worker-01",
            "name": "Custom Worker Contract",
            "description": "Custom tasks",
            "allowed_tools": ["custom.run"],
            "forbidden_tools": ["shell.exec"],
            "risk_level": "medium",
            "enabled": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "custom-worker-01"
        assert "custom.run" in data["allowed_tools"]

        # Verify via GET
        get_res = await client.get("/contracts/custom-worker-01")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Custom Worker Contract"


@pytest.mark.asyncio
async def test_invalid_contract_returns_validation_error():
    """20. PUT /contracts/{agent_id} with invalid body returns HTTP 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/contracts/agent-x", json={
            "name": 123,  # missing required fields like agent_id
        })
        assert resp.status_code == 422
