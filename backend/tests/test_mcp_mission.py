import json
import pytest

from backend.app.db.repository import InMemoryRepository, set_repository, get_repository
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    set_contract_repository,
    get_contract_repository,
)
from backend.app.provenance.tracker import set_provenance_tracker, ProvenanceTracker
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentStatus
from backend.app.schemas.contract import ContractUpdate
from backend.app.api.missions import ensure_foundational_agents
from backend.app.mcp.server import create_mcp_server
from backend.app.ledger.verifier import verify_ledger_chain


@pytest.fixture(autouse=True)
def setup_environment():
    """Reset repository, contracts, provenance tracker, and PDP engine for each test."""
    repo = InMemoryRepository()
    set_repository(repo)
    set_contract_repository(InMemoryContractRepository(seed=True))
    set_provenance_tracker(ProvenanceTracker())
    set_pdp(PolicyDecisionPoint())


@pytest.mark.asyncio
async def test_mcp_mission_tool_discovery():
    """
    Test 1: Tool Discovery
    Verify that aegismesh_run_mission is exposed by the MCP server alongside aegismesh_enforce.
    """
    server = create_mcp_server(in_process=True)
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]

    assert "aegismesh_run_mission" in tool_names
    assert "aegismesh_enforce" in tool_names

    mission_tool = next(t for t in tools if t.name == "aegismesh_run_mission")
    assert mission_tool.description is not None
    assert "Planner -> Researcher -> Executor" in mission_tool.description


@pytest.mark.asyncio
async def test_mcp_run_mission_normal_completed():
    """
    Test 2 & 3 & 4 & 5 & 6: Normal Mission (All Agents Allowed)
    Invokes MissionCoordinator through aegismesh_run_mission.
    Verifies:
      - status is COMPLETED
      - mission_id and session_id are preserved and consistent
      - planner_result, researcher_result, and executor_result are returned
      - execution_trace contains 3 sequential steps
      - real event_ids are captured from PEP decisions
      - ledger hash chain is unbroken
    """
    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_run_mission",
        arguments={
            "goal": "Investigate emerging agentic security risks and produce briefing",
            "mission_id": "mcp-mission-normal-01",
            "session_id": "mcp-session-normal-01",
        },
    )

    assert res.is_error is False
    assert len(res.content) > 0
    data = json.loads(res.content[0].text)

    # Core mission metadata
    assert data["status"] == "COMPLETED"
    assert data["mission_id"] == "mcp-mission-normal-01"
    assert data["session_id"] == "mcp-session-normal-01"
    assert data["goal"] == "Investigate emerging agentic security risks and produce briefing"
    assert data["error"] is None

    # Verify all agent outputs populated
    assert data["planner_result"] is not None
    assert data["planner_result"]["status"] == "delegated"
    assert data["planner_result"]["target_agent"] == "researcher-01"

    assert data["researcher_result"] is not None
    assert data["researcher_result"]["status"] == "success"
    assert len(data["researcher_result"]["results"]) > 0

    assert data["executor_result"] is not None
    assert data["executor_result"]["status"] == "generated"
    assert "AegisMesh" in data["executor_result"]["content"]

    # Verify execution trace
    trace = data["execution_trace"]
    assert len(trace) == 3
    assert trace[0]["agent_id"] == "planner-01"
    assert trace[0]["action"] == "task.delegate"
    assert trace[0]["decision"] == "ALLOW"
    assert trace[1]["agent_id"] == "researcher-01"
    assert trace[1]["action"] == "web.search"
    assert trace[1]["decision"] == "ALLOW"
    assert trace[2]["agent_id"] == "executor-01"
    assert trace[2]["action"] == "report.generate"
    assert trace[2]["decision"] == "ALLOW"

    # Verify event IDs captured
    event_ids = data["event_ids"]
    assert len(event_ids) == 3
    assert len(set(event_ids)) == 3  # Unique event IDs

    # Verify cryptographic ledger events exist and chain verifies
    repo = get_repository()
    for eid in event_ids:
        event = await repo.get_event(eid)
        assert event is not None
        assert event.event_type == "enforcement"

    events = await repo.list_events()
    events_dict = [ev.model_dump() for ev in events]
    report = verify_ledger_chain(events_dict)
    assert report["ok"] is True
    assert report["chain_valid"] is True
    assert report["checked"] >= 3


@pytest.mark.asyncio
async def test_mcp_run_mission_planner_blocked():
    """
    Test 7A: Planner Blocked
    When PlannerAgent is blocked by policy/contract:
      - Mission halts immediately
      - Researcher and Executor are NEVER executed
      - Status is BLOCKED
    """
    await ensure_foundational_agents()
    contract_repo = get_contract_repository()
    # Forbid task.delegate on planner
    updated = await contract_repo.update_contract(
        "planner-01",
        ContractUpdate(forbidden_tools=["task.delegate"]),
    )
    assert updated is not None

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_run_mission",
        arguments={
            "goal": "Mission with unauthorized planner delegation",
            "mission_id": "mcp-mission-plan-block",
        },
    )

    data = json.loads(res.content[0].text)
    assert data["status"] == "BLOCKED"
    assert data["planner_result"] is None
    assert data["researcher_result"] is None
    assert data["executor_result"] is None
    assert data["error"] is not None
    assert len(data["event_ids"]) == 1

    # Verify trace shows step 1 BLOCKED
    trace = data["execution_trace"]
    assert len(trace) == 1
    assert trace[0]["agent_id"] == "planner-01"
    assert trace[0]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_mcp_run_mission_researcher_blocked():
    """
    Test 7B: Researcher Blocked
    When Planner succeeds but ResearcherAgent is blocked:
      - Mission halts at step 2
      - Executor is NEVER executed
      - Status is BLOCKED
    """
    await ensure_foundational_agents()
    contract_repo = get_contract_repository()
    # Forbid web.search on researcher
    updated = await contract_repo.update_contract(
        "researcher-01",
        ContractUpdate(forbidden_tools=["web.search"]),
    )
    assert updated is not None

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_run_mission",
        arguments={
            "goal": "Mission with restricted researcher queries",
            "mission_id": "mcp-mission-res-block",
        },
    )

    data = json.loads(res.content[0].text)
    assert data["status"] == "BLOCKED"
    assert data["planner_result"] is not None
    assert data["researcher_result"] is None
    assert data["executor_result"] is None

    # Trace shows step 1 ALLOW, step 2 BLOCKED
    trace = data["execution_trace"]
    assert len(trace) == 2
    assert trace[0]["agent_id"] == "planner-01"
    assert trace[0]["status"] == "ALLOW"
    assert trace[1]["agent_id"] == "researcher-01"
    assert trace[1]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_mcp_run_mission_executor_blocked():
    """
    Test 7C: Executor Blocked
    When Planner and Researcher succeed but ExecutorAgent is blocked:
      - Mission halts at step 3
      - Status is BLOCKED
    """
    await ensure_foundational_agents()
    contract_repo = get_contract_repository()
    # Forbid report.generate on executor
    updated = await contract_repo.update_contract(
        "executor-01",
        ContractUpdate(forbidden_tools=["report.generate"]),
    )
    assert updated is not None

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_run_mission",
        arguments={
            "goal": "Mission with unauthorized artifact synthesis",
            "mission_id": "mcp-mission-exec-block",
        },
    )

    data = json.loads(res.content[0].text)
    assert data["status"] == "BLOCKED"
    assert data["planner_result"] is not None
    assert data["researcher_result"] is not None
    assert data["executor_result"] is None

    trace = data["execution_trace"]
    assert len(trace) == 3
    assert trace[0]["status"] == "ALLOW"
    assert trace[1]["status"] == "ALLOW"
    assert trace[2]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_mcp_run_mission_quarantined_agent():
    """
    Test 8: Quarantined Agent
    When researcher-01 is QUARANTINED in repository:
      - Mission halts with QUARANTINED
      - Downstream Executor is NOT executed
      - Real quarantine reason returned
    """
    await ensure_foundational_agents()
    repo = get_repository()
    await repo.update_agent_status("researcher-01", AgentStatus.QUARANTINED)

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_run_mission",
        arguments={
            "goal": "Mission involving compromised quarantined agent",
            "mission_id": "mcp-mission-quarantine",
        },
    )

    data = json.loads(res.content[0].text)
    assert data["status"] == "QUARANTINED"
    assert data["planner_result"] is not None
    assert data["researcher_result"] is None
    assert data["executor_result"] is None
    assert "quarantined" in data["error"].lower()

    trace = data["execution_trace"]
    assert len(trace) == 2
    assert trace[0]["status"] == "ALLOW"
    assert trace[1]["status"] == "QUARANTINED"


@pytest.mark.asyncio
async def test_mcp_run_mission_ledger_integrity_no_bypass():
    """
    Test 9 & 10: Ledger Integrity and No Bypass
    Verify that MCP does not fabricate mission decisions and that all PEP
    evaluations link into the cryptographic ledger chain.
    """
    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_run_mission",
        arguments={
            "goal": "Cryptographic ledger audit mission",
            "mission_id": "mcp-mission-audit-01",
        },
    )

    data = json.loads(res.content[0].text)
    assert data["status"] == "COMPLETED"

    repo = get_repository()
    events = await repo.list_events()
    events_dict = [ev.model_dump() for ev in events]

    # Verify ledger chain is valid across all mission events
    verification = verify_ledger_chain(events_dict)
    assert verification["ok"] is True
    assert verification["chain_valid"] is True
    assert verification["checked"] == 3
