import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository, get_repository
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    set_contract_repository,
    get_contract_repository,
    ContractCreate,
)
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentCreate, AgentStatus
from backend.app.schemas.decision import DecisionReason, DecisionStatus, RiskLevel
from backend.app.security.exceptions import (
    ActionDenied,
    AgentQuarantined,
    ApprovalRequired,
    InvalidAgentIdentity,
    SecurityError,
)
from agents.common.client import AegisMeshClient
from agents.planner.agent import PlannerAgent
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent
from agents.orchestrator.runner import MissionCoordinator, MissionResult


@pytest.fixture(autouse=True)
def setup_environment():
    """Reset repository, contract repository, and PDP for fresh isolation."""
    repo = InMemoryRepository()
    set_repository(repo)
    set_contract_repository(InMemoryContractRepository(seed=True))
    set_pdp(PolicyDecisionPoint())


# ---------------------------------------------------------------------------
# Unit / Guarded Workflow Tests (Mocks & Exact Fail-Closed Flow)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_happy_path_all_agents_allowed():
    """
    Happy Path:
    Planner -> ALLOW
    Researcher -> ALLOW
    Executor -> ALLOW

    Verify:
    - mission completes with status "COMPLETED"
    - all three agents executed in sequence
    - same mission_id and session_id propagated to all actions
    - cryptographic event IDs captured from PEP decisions
    """
    mock_client = MagicMock(spec=AegisMeshClient)

    # Return valid ALLOW decisions with unique event IDs
    async def mock_enforce(action_request):
        req_dict = action_request if isinstance(action_request, dict) else action_request.model_dump()
        action = req_dict["action"]
        agent_id = req_dict["agent_id"]
        event_map = {
            "task.delegate": "evt-plan-001",
            "web.search": "evt-res-002",
            "report.generate": "evt-exec-003",
        }
        return {
            "decision": DecisionStatus.ALLOW.value,
            "allowed": True,
            "reason": DecisionReason.ALLOWED_BY_POLICY.value,
            "risk_level": RiskLevel.LOW.value,
            "agent_id": agent_id,
            "action": action,
            "event_id": event_map.get(action, "evt-default"),
            "details": {},
        }

    mock_client.enforce = AsyncMock(side_effect=mock_enforce)

    planner = PlannerAgent(agent_id="planner-01", client=mock_client)
    researcher = ResearcherAgent(agent_id="researcher-01", client=mock_client)
    executor = ExecutorAgent(agent_id="executor-01", client=mock_client)

    coordinator = MissionCoordinator(
        planner=planner,
        researcher=researcher,
        executor=executor,
        client=mock_client,
    )

    goal = "Investigate supply chain zero-day vulnerabilities"
    mission_id = "mission-happy-100"
    session_id = "session-happy-200"

    result = await coordinator.run_mission(
        goal=goal,
        mission_id=mission_id,
        session_id=session_id,
    )

    # Verify status and propagation
    assert result.status == "COMPLETED"
    assert result.mission_id == mission_id
    assert result.session_id == session_id
    assert result.goal == goal
    assert result.error is None

    # Verify all 3 results populated
    assert result.planner_result is not None
    assert result.planner_result["status"] == "delegated"
    assert result.researcher_result is not None
    assert result.researcher_result["status"] == "success"
    assert result.executor_result is not None
    assert result.executor_result["status"] == "generated"
    assert "AegisMesh" in result.executor_result["content"]

    # Verify event IDs captured
    assert result.event_ids == ["evt-plan-001", "evt-res-002", "evt-exec-003"]

    # Verify enforce was called exactly 3 times with matching mission/session
    assert mock_client.enforce.call_count == 3
    for call_args in mock_client.enforce.call_args_list:
        req = call_args[0][0]
        assert req.mission_id == mission_id
        assert req.session_id == session_id

    # Verify execution trace
    assert len(result.execution_trace) == 3
    assert result.execution_trace[0]["agent_id"] == "planner-01"
    assert result.execution_trace[0]["action"] == "task.delegate"
    assert result.execution_trace[1]["agent_id"] == "researcher-01"
    assert result.execution_trace[1]["action"] == "web.search"
    assert result.execution_trace[2]["agent_id"] == "executor-01"
    assert result.execution_trace[2]["action"] == "report.generate"


@pytest.mark.asyncio
async def test_planner_blocked_stops_mission():
    """
    Planner Blocked:
    Planner -> BLOCK
    Mission stops
    Researcher does NOT execute
    Executor does NOT execute
    """
    mock_client = MagicMock(spec=AegisMeshClient)
    mock_client.enforce = AsyncMock(return_value={
        "decision": DecisionStatus.BLOCK.value,
        "allowed": False,
        "reason": DecisionReason.POLICY_VIOLATION.value,
        "risk_level": RiskLevel.HIGH.value,
        "agent_id": "planner-01",
        "action": "task.delegate",
        "event_id": "evt-block-001",
        "details": {"rule": "deny_delegation"},
    })

    planner = PlannerAgent(agent_id="planner-01", client=mock_client)
    researcher = ResearcherAgent(agent_id="researcher-01", client=mock_client)
    executor = ExecutorAgent(agent_id="executor-01", client=mock_client)

    # Spy on researcher and executor
    researcher.execute_web_search = AsyncMock()
    executor.execute_generate_report = AsyncMock()

    coordinator = MissionCoordinator(
        planner=planner,
        researcher=researcher,
        executor=executor,
        client=mock_client,
    )

    result = await coordinator.run_mission(goal="Unauthorized delegation goal")

    assert result.status == "BLOCKED"
    assert "blocked" in result.error.lower() or "POLICY_VIOLATION" in result.error
    assert result.planner_result is None
    assert result.researcher_result is None
    assert result.executor_result is None

    # Downstream agents were NEVER invoked
    researcher.execute_web_search.assert_not_called()
    executor.execute_generate_report.assert_not_called()
    assert mock_client.enforce.call_count == 1
    assert result.event_ids == ["evt-block-001"]


@pytest.mark.asyncio
async def test_researcher_blocked_stops_mission():
    """
    Researcher Blocked:
    Planner -> ALLOW
    Researcher -> BLOCK
    Executor does NOT execute
    """
    mock_client = MagicMock(spec=AegisMeshClient)

    async def mock_enforce(action_request):
        req_dict = action_request if isinstance(action_request, dict) else action_request.model_dump()
        action = req_dict["action"]
        if action == "task.delegate":
            return {
                "decision": DecisionStatus.ALLOW.value,
                "allowed": True,
                "reason": DecisionReason.ALLOWED_BY_POLICY.value,
                "risk_level": RiskLevel.LOW.value,
                "agent_id": "planner-01",
                "action": action,
                "event_id": "evt-plan-001",
                "details": {},
            }
        else:
            return {
                "decision": DecisionStatus.BLOCK.value,
                "allowed": False,
                "reason": DecisionReason.CONTRACT_VIOLATION.value,
                "risk_level": RiskLevel.HIGH.value,
                "agent_id": "researcher-01",
                "action": action,
                "event_id": "evt-res-block",
                "details": {"violation": "restricted query target"},
            }

    mock_client.enforce = AsyncMock(side_effect=mock_enforce)

    planner = PlannerAgent(agent_id="planner-01", client=mock_client)
    researcher = ResearcherAgent(agent_id="researcher-01", client=mock_client)
    executor = ExecutorAgent(agent_id="executor-01", client=mock_client)

    executor.execute_generate_report = AsyncMock()

    coordinator = MissionCoordinator(
        planner=planner,
        researcher=researcher,
        executor=executor,
        client=mock_client,
    )

    result = await coordinator.run_mission(goal="Targeted restricted intelligence")

    assert result.status == "BLOCKED"
    assert result.planner_result is not None
    assert result.researcher_result is None
    assert result.executor_result is None

    # Executor was NEVER called
    executor.execute_generate_report.assert_not_called()
    assert mock_client.enforce.call_count == 2
    assert "evt-plan-001" in result.event_ids
    assert "evt-res-block" in result.event_ids


@pytest.mark.asyncio
async def test_executor_blocked_mission_does_not_succeed():
    """
    Executor Blocked:
    Planner -> ALLOW
    Researcher -> ALLOW
    Executor -> BLOCK
    Mission does not complete successfully
    """
    mock_client = MagicMock(spec=AegisMeshClient)

    async def mock_enforce(action_request):
        req_dict = action_request if isinstance(action_request, dict) else action_request.model_dump()
        action = req_dict["action"]
        if action in ("task.delegate", "web.search"):
            return {
                "decision": DecisionStatus.ALLOW.value,
                "allowed": True,
                "reason": DecisionReason.ALLOWED_BY_POLICY.value,
                "risk_level": RiskLevel.LOW.value,
                "agent_id": req_dict["agent_id"],
                "action": action,
                "event_id": f"evt-{action}",
                "details": {},
            }
        else:
            return {
                "decision": DecisionStatus.BLOCK.value,
                "allowed": False,
                "reason": DecisionReason.HIGH_RISK_ACTION.value,
                "risk_level": RiskLevel.HIGH.value,
                "agent_id": "executor-01",
                "action": action,
                "event_id": "evt-exec-blocked",
                "details": {"message": "Blocked template"},
            }

    mock_client.enforce = AsyncMock(side_effect=mock_enforce)

    planner = PlannerAgent(agent_id="planner-01", client=mock_client)
    researcher = ResearcherAgent(agent_id="researcher-01", client=mock_client)
    executor = ExecutorAgent(agent_id="executor-01", client=mock_client)

    coordinator = MissionCoordinator(
        planner=planner,
        researcher=researcher,
        executor=executor,
        client=mock_client,
    )

    result = await coordinator.run_mission(goal="Generate restricted briefing")

    assert result.status == "BLOCKED"
    assert result.planner_result is not None
    assert result.researcher_result is not None
    assert result.executor_result is None
    assert mock_client.enforce.call_count == 3
    assert "evt-exec-blocked" in result.event_ids


@pytest.mark.asyncio
async def test_quarantined_agent_stops_mission():
    """
    Quarantined Agent:
    Researcher is quarantined.
    Planner -> ALLOW
    Researcher -> QUARANTINE -> Mission halts immediately
    Executor is NOT executed
    """
    mock_client = MagicMock(spec=AegisMeshClient)

    async def mock_enforce(action_request):
        req_dict = action_request if isinstance(action_request, dict) else action_request.model_dump()
        action = req_dict["action"]
        if action == "task.delegate":
            return {
                "decision": DecisionStatus.ALLOW.value,
                "allowed": True,
                "reason": DecisionReason.ALLOWED_BY_POLICY.value,
                "risk_level": RiskLevel.LOW.value,
                "agent_id": "planner-01",
                "action": action,
                "event_id": "evt-plan-001",
                "details": {},
            }
        else:
            return {
                "decision": DecisionStatus.QUARANTINE.value,
                "allowed": False,
                "reason": DecisionReason.AGENT_QUARANTINED.value,
                "risk_level": RiskLevel.CRITICAL.value,
                "agent_id": "researcher-01",
                "action": action,
                "event_id": "evt-quarantine-001",
                "details": {"incident_id": "inc-rogue-01"},
            }

    mock_client.enforce = AsyncMock(side_effect=mock_enforce)

    planner = PlannerAgent(agent_id="planner-01", client=mock_client)
    researcher = ResearcherAgent(agent_id="researcher-01", client=mock_client)
    executor = ExecutorAgent(agent_id="executor-01", client=mock_client)

    executor.execute_generate_report = AsyncMock()

    coordinator = MissionCoordinator(
        planner=planner,
        researcher=researcher,
        executor=executor,
        client=mock_client,
    )

    result = await coordinator.run_mission(goal="Mission with quarantined agent")

    assert result.status == "QUARANTINED"
    assert "quarantined" in result.error.lower()
    assert result.planner_result is not None
    assert result.researcher_result is None
    assert result.executor_result is None
    executor.execute_generate_report.assert_not_called()
    assert "evt-quarantine-001" in result.event_ids


# ---------------------------------------------------------------------------
# End-to-End Real Backend Integration Test (No Mocks on PEP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_backend_mission_integration():
    """
    End-to-End Integration Verification:
    Runs a real mission against the in-process FastAPI app using AegisMeshClient(app=app).
    Verifies that:
    1. planner-01 executes task.delegate through PEP -> ALLOW
    2. researcher-01 executes web.search through PEP -> ALLOW
    3. executor-01 executes report.generate through PEP -> ALLOW
    4. Mission status is COMPLETED
    5. All actions correlate to the exact same mission_id and session_id
    6. Tamper-proof ledger events were recorded and verified
    """
    # 1. Setup real registered agents and contracts
    client = AegisMeshClient(app=app)

    await client.register_agent(
        agent_id="planner-01",
        name="Planner Agent",
        role="planner",
        capabilities=["task.delegate", "plan.declare"],
    )
    await client.register_agent(
        agent_id="researcher-01",
        name="Researcher Agent",
        role="researcher",
        capabilities=["web.search", "web.read"],
    )
    await client.register_agent(
        agent_id="executor-01",
        name="Executor Agent",
        role="executor",
        capabilities=["report.generate", "fs.read"],
    )

    # 2. Instantiate real agents and coordinator
    planner = PlannerAgent(agent_id="planner-01", client=client)
    researcher = ResearcherAgent(agent_id="researcher-01", client=client)
    executor = ExecutorAgent(agent_id="executor-01", client=client)

    coordinator = MissionCoordinator(
        planner=planner,
        researcher=researcher,
        executor=executor,
        client=client,
    )

    test_goal = "Analyze autonomous agent runtime security integrity"
    mission_id = "mission-e2e-live-01"
    session_id = "session-e2e-live-01"

    # 3. Run mission
    result = await coordinator.run_mission(
        goal=test_goal,
        mission_id=mission_id,
        session_id=session_id,
    )

    # 4. Assert end-to-end mission success
    assert result.status == "COMPLETED"
    assert result.mission_id == mission_id
    assert result.session_id == session_id
    assert result.goal == test_goal
    assert result.error is None

    # Check that each agent produced real output
    assert result.planner_result["status"] == "delegated"
    assert result.planner_result["target_agent"] == "researcher-01"
    assert result.researcher_result["status"] == "success"
    assert len(result.researcher_result["results"]) > 0
    assert result.executor_result["status"] == "generated"
    assert "AegisMesh" in result.executor_result["content"]

    # 5. Check cryptographic ledger events
    assert len(result.event_ids) == 3
    for eid in result.event_ids:
        assert eid.startswith("evt-") or len(eid) > 0

    # 6. Verify ledger integrity endpoint
    ledger_status = await client.verify_ledger()
    assert ledger_status.get("ok") is True
    assert ledger_status.get("chain_valid") is True
    assert ledger_status.get("checked") == 3
