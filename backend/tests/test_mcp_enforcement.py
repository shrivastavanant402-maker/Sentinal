import json
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository, get_repository
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    set_contract_repository,
    get_contract_repository,
)
from backend.app.provenance.tracker import set_provenance_tracker, ProvenanceTracker
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentCreate, AgentStatus
from backend.app.schemas.decision import DecisionReason, DecisionStatus, RiskLevel
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
async def test_mcp_tool_registration_discovery():
    """
    Test A: Tool Registration / Discovery
    Verify that the MCP server exposes the `aegismesh_enforce` tool.
    """
    server = create_mcp_server(in_process=True)
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]

    assert "aegismesh_enforce" in tool_names
    enforce_tool = next(t for t in tools if t.name == "aegismesh_enforce")
    assert enforce_tool.description is not None
    assert "AegisMesh runtime security policy" in enforce_tool.description


@pytest.mark.asyncio
async def test_mcp_allowed_action():
    """
    Test B: Allowed Action
    Registered agent `researcher-01` requests permitted tool `web.search`.
    Verify real ALLOW decision through PEP without bypass.
    """
    repo = get_repository()
    await repo.register_agent(
        AgentCreate(
            id="researcher-01",
            name="Deep Researcher",
            role="researcher",
            capabilities=["web.search", "web.read"],
        )
    )

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_enforce",
        arguments={
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "Zero day vulnerabilities"},
            "mission_id": "mission-mcp-01",
            "session_id": "session-mcp-01",
        },
    )

    assert res.is_error is False
    assert len(res.content) > 0
    decision_data = json.loads(res.content[0].text)

    assert decision_data["decision"] == "ALLOW"
    assert decision_data["allowed"] is True
    assert decision_data["agent_id"] == "researcher-01"
    assert decision_data["action"] == "web.search"
    assert decision_data["event_id"] is not None
    assert decision_data["risk_level"] == "low"


@pytest.mark.asyncio
async def test_mcp_blocked_action():
    """
    Test C: Blocked Action
    Registered agent `researcher-01` attempts high-risk tool `shell.exec`.
    Verify real BLOCK decision returned through PEP.
    """
    repo = get_repository()
    await repo.register_agent(
        AgentCreate(
            id="researcher-01",
            name="Deep Researcher",
            role="researcher",
            capabilities=["web.search"],
        )
    )

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_enforce",
        arguments={
            "agent_id": "researcher-01",
            "action": "shell.exec",
            "payload": {"command": "rm -rf /"},
            "mission_id": "mission-mcp-02",
        },
    )

    assert res.is_error is False
    decision_data = json.loads(res.content[0].text)

    assert decision_data["decision"] == "BLOCK"
    assert decision_data["allowed"] is False
    assert decision_data["agent_id"] == "researcher-01"
    assert decision_data["action"] == "shell.exec"
    assert decision_data["event_id"] is not None
    # Action is forbidden by contract or policy drift
    assert decision_data["reason"] in (
        "MISSION_DRIFT",
        "CONTRACT_VIOLATION",
        "POLICY_VIOLATION",
        "HIGH_RISK_ACTION",
        "TAINT_SENSITIVE_LEAK",
    )


@pytest.mark.asyncio
async def test_mcp_unknown_agent_invalid_identity():
    """
    Test D: Unknown Agent
    Unregistered agent `unknown-agent-99` attempts an action.
    Verify INVALID_IDENTITY and BLOCK returned.
    """
    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_enforce",
        arguments={
            "agent_id": "unknown-agent-99",
            "action": "web.search",
            "payload": {"query": "classified leaks"},
        },
    )

    decision_data = json.loads(res.content[0].text)

    assert decision_data["decision"] == "BLOCK"
    assert decision_data["allowed"] is False
    assert decision_data["reason"] == "INVALID_IDENTITY"
    assert decision_data["agent_id"] == "unknown-agent-99"


@pytest.mark.asyncio
async def test_mcp_ledger_integration():
    """
    Test E: Cryptographic Ledger Integration
    Verify an MCP enforcement call produces a real ledger event that links
    into the immutable hash chain.
    """
    repo = get_repository()
    await repo.register_agent(
        AgentCreate(
            id="researcher-01",
            name="Deep Researcher",
            role="researcher",
            capabilities=["web.search"],
        )
    )

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_enforce",
        arguments={
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "Ledger proof check"},
            "mission_id": "mission-ledger-test",
            "session_id": "session-ledger-test",
        },
    )

    decision_data = json.loads(res.content[0].text)
    event_id = decision_data["event_id"]
    assert event_id is not None

    # Fetch event directly from the repository
    event = await repo.get_event(event_id)
    assert event is not None
    assert event.agent_id == "researcher-01"
    assert event.action == "web.search"
    assert event.event_type == "enforcement"
    assert event.event_hash is not None

    # Verify ledger chain integrity
    events = await repo.list_events()
    events_dict = [ev.model_dump() for ev in events]
    report = verify_ledger_chain(events_dict)
    assert report["ok"] is True
    assert report["chain_valid"] is True
    assert report["checked"] >= 1


@pytest.mark.asyncio
async def test_mcp_no_bypass():
    """
    Test F: No Bypass
    Verify that quarantined agent status set in the real repository causes
    the MCP tool to return QUARANTINE (proving it executes the real PDP path).
    """
    repo = get_repository()
    await repo.register_agent(
        AgentCreate(
            id="quarantined-researcher",
            name="Compromised Researcher",
            role="researcher",
            capabilities=["web.search"],
        )
    )
    await repo.update_agent_status("quarantined-researcher", AgentStatus.QUARANTINED)

    server = create_mcp_server(in_process=True)
    res = await server.call_tool(
        "aegismesh_enforce",
        arguments={
            "agent_id": "quarantined-researcher",
            "action": "web.search",
            "payload": {},
        },
    )

    decision_data = json.loads(res.content[0].text)

    assert decision_data["decision"] == "QUARANTINE"
    assert decision_data["allowed"] is False
    assert decision_data["reason"] == "AGENT_QUARANTINED"
    assert decision_data["risk_level"] == "critical"
