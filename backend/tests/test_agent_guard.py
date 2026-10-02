from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, ConnectError, HTTPStatusError, Request, Response

from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository
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
from agents.common.base import BaseAgent
from agents.common.client import AegisMeshClient
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent
from agents.planner.agent import PlannerAgent


# ---------------------------------------------------------------------------
# Test Agent Implementation for Generic Guard Testing
# ---------------------------------------------------------------------------

class MockProtectedAgent(BaseAgent):
    """Concrete mock agent used for unit testing PEP guard behavior."""
    def __init__(self, agent_id="test-agent-01", client=None):
        super().__init__(
            agent_id=agent_id,
            name="Test Agent",
            role="tester",
            capabilities=["test.safe", "test.risky"],
            client=client,
        )

    async def run_step(self, session_id=None, **kwargs):
        return {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_environment():
    repo = InMemoryRepository()
    set_repository(repo)
    set_pdp(PolicyDecisionPoint())


# ---------------------------------------------------------------------------
# 7. Action Execution Test Double (CASES A - F)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_a_pep_allow_executes_tool_exactly_once():
    """CASE A: PEP returns ALLOW -> protected tool executes exactly once."""
    mock_client = MagicMock(spec=AegisMeshClient)
    mock_client.enforce = AsyncMock(return_value={
        "decision": DecisionStatus.ALLOW.value,
        "allowed": True,
        "reason": DecisionReason.ALLOWED_BY_POLICY.value,
        "risk_level": RiskLevel.LOW.value,
        "agent_id": "test-agent-01",
        "action": "test.safe",
        "event_id": "evt-001",
        "details": {},
    })

    agent = MockProtectedAgent(client=mock_client)
    mock_tool = MagicMock(return_value={"result": "success"})

    result = await agent.execute_protected(
        action="test.safe",
        payload={"param": 1},
        executor=mock_tool,
        arg1="val1",
    )

    assert result == {"result": "success"}
    assert mock_tool.call_count == 1
    mock_tool.assert_called_once_with(arg1="val1")


@pytest.mark.asyncio
async def test_case_b_pep_block_executes_tool_zero_times():
    """CASE B: PEP returns BLOCK -> ActionDenied raised, tool executes ZERO times."""
    mock_client = MagicMock(spec=AegisMeshClient)
    mock_client.enforce = AsyncMock(return_value={
        "decision": DecisionStatus.BLOCK.value,
        "allowed": False,
        "reason": DecisionReason.HIGH_RISK_ACTION.value,
        "risk_level": RiskLevel.HIGH.value,
        "agent_id": "test-agent-01",
        "action": "test.risky",
        "event_id": "evt-002",
        "details": {"message": "Blocked by policy"},
    })

    agent = MockProtectedAgent(client=mock_client)
    mock_tool = MagicMock(return_value={"result": "should_never_run"})

    with pytest.raises(ActionDenied) as exc_info:
        await agent.execute_protected(
            action="test.risky",
            payload={},
            executor=mock_tool,
        )

    assert "HIGH_RISK_ACTION" in str(exc_info.value)
    assert mock_tool.call_count == 0


@pytest.mark.asyncio
async def test_case_c_pep_quarantine_executes_tool_zero_times():
    """CASE C: PEP returns QUARANTINE -> AgentQuarantined raised, tool executes ZERO times."""
    mock_client = MagicMock(spec=AegisMeshClient)
    mock_client.enforce = AsyncMock(return_value={
        "decision": DecisionStatus.QUARANTINE.value,
        "allowed": False,
        "reason": DecisionReason.AGENT_QUARANTINED.value,
        "risk_level": RiskLevel.CRITICAL.value,
        "agent_id": "test-agent-01",
        "action": "test.safe",
        "event_id": "evt-003",
        "details": {"agent_status": "quarantined"},
    })

    agent = MockProtectedAgent(client=mock_client)
    mock_tool = MagicMock(return_value={"result": "should_never_run"})

    with pytest.raises(AgentQuarantined) as exc_info:
        await agent.execute_protected(
            action="test.safe",
            payload={},
            executor=mock_tool,
        )

    assert "quarantined" in str(exc_info.value).lower()
    assert mock_tool.call_count == 0


@pytest.mark.asyncio
async def test_case_d_pep_approval_executes_tool_zero_times():
    """CASE D: PEP returns APPROVAL -> ApprovalRequired raised, tool executes ZERO times."""
    mock_client = MagicMock(spec=AegisMeshClient)
    mock_client.enforce = AsyncMock(return_value={
        "decision": DecisionStatus.APPROVAL.value,
        "allowed": False,
        "reason": DecisionReason.HIGH_RISK_ACTION.value,
        "risk_level": RiskLevel.HIGH.value,
        "agent_id": "test-agent-01",
        "action": "test.admin",
        "event_id": "evt-004",
        "details": {"required_role": "admin"},
    })

    agent = MockProtectedAgent(client=mock_client)
    mock_tool = MagicMock(return_value={"result": "should_never_run"})

    with pytest.raises(ApprovalRequired) as exc_info:
        await agent.execute_protected(
            action="test.admin",
            payload={},
            executor=mock_tool,
        )

    assert "approval" in str(exc_info.value).lower()
    assert mock_tool.call_count == 0


@pytest.mark.asyncio
async def test_case_e_pep_unavailable_fails_closed_zero_executions():
    """CASE E: PEP is unavailable/connection error -> ActionDenied raised (FAIL CLOSED), tool executes ZERO times."""
    mock_client = MagicMock(spec=AegisMeshClient)
    mock_client.enforce = AsyncMock(side_effect=ConnectError("Connection refused to PEP:8000"))

    agent = MockProtectedAgent(client=mock_client)
    mock_tool = MagicMock(return_value={"result": "should_never_run"})

    with pytest.raises(ActionDenied) as exc_info:
        await agent.execute_protected(
            action="test.safe",
            payload={},
            executor=mock_tool,
        )

    assert "fail-closed" in str(exc_info.value).lower()
    assert mock_tool.call_count == 0


@pytest.mark.asyncio
async def test_case_f_pep_malformed_decision_fails_closed_zero_executions():
    """CASE F: PEP returns malformed/unknown data -> ActionDenied raised (FAIL CLOSED), tool executes ZERO times."""
    mock_client = MagicMock(spec=AegisMeshClient)
    # Missing required 'decision' and 'allowed' fields
    mock_client.enforce = AsyncMock(return_value={"corrupted": "payload", "status": "unknown"})

    agent = MockProtectedAgent(client=mock_client)
    mock_tool = MagicMock(return_value={"result": "should_never_run"})

    with pytest.raises(ActionDenied) as exc_info:
        await agent.execute_protected(
            action="test.safe",
            payload={},
            executor=mock_tool,
        )

    assert "malformed" in str(exc_info.value).lower()
    assert mock_tool.call_count == 0


# ---------------------------------------------------------------------------
# 8. Real Agents Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_researcher_safe_action_allowed_and_executes():
    """Researcher: registered agent + safe action (web.search) -> ALLOW -> executes web search."""
    client = AegisMeshClient(app=app)
    # Register researcher-01
    await client.register_agent(
        agent_id="researcher-01",
        name="Deep Researcher",
        role="researcher",
        capabilities=["web.search", "web.read"],
    )

    researcher = ResearcherAgent(agent_id="researcher-01", client=client)

    # 1. Direct guard verification
    decision = await researcher.guard(
        action="web.search",
        payload={"query": "AI integrity"},
    )
    assert decision.decision == DecisionStatus.ALLOW
    assert decision.allowed is True

    # 2. Protected tool execution
    search_result = await researcher.execute_web_search(query="AI integrity", max_results=3)
    assert search_result["status"] == "success"
    assert search_result["query"] == "AI integrity"
    assert len(search_result["results"]) > 0


@pytest.mark.asyncio
async def test_researcher_high_risk_action_blocked_and_does_not_execute():
    """Researcher: high-risk action (database.export) -> BLOCK -> ActionDenied -> tool does NOT execute."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="researcher-01",
        name="Deep Researcher",
        role="researcher",
        capabilities=["web.search"],
    )

    researcher = ResearcherAgent(agent_id="researcher-01", client=client)

    # Calling execute_database_export must be blocked by the PEP guard
    with pytest.raises(ActionDenied) as exc_info:
        await researcher.execute_database_export(table="sensitive_credentials")

    assert "HIGH_RISK_ACTION" in str(exc_info.value) or "blocked" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_unknown_agent_blocked_with_invalid_identity():
    """Unknown agent: calling guard -> BLOCK -> InvalidAgentIdentity raised."""
    client = AegisMeshClient(app=app)
    # ghost-agent-99 is never registered
    unregistered_agent = ResearcherAgent(agent_id="ghost-agent-99", client=client)

    with pytest.raises(InvalidAgentIdentity) as exc_info:
        await unregistered_agent.execute_web_search(query="secret query")

    assert "invalid agent identity" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_quarantined_agent_blocked_with_quarantined_exception():
    """Quarantined agent: calling guard -> QUARANTINE -> AgentQuarantined raised."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="compromised-agent-01",
        name="Compromised Researcher",
        role="researcher",
        capabilities=["web.search"],
    )
    # Set status to quarantined
    repo = InMemoryRepository()
    from backend.app.db.repository import get_repository
    active_repo = get_repository()
    await active_repo.update_agent_status("compromised-agent-01", AgentStatus.QUARANTINED)

    quarantined_agent = ResearcherAgent(agent_id="compromised-agent-01", client=client)

    with pytest.raises(AgentQuarantined) as exc_info:
        await quarantined_agent.execute_web_search(query="exfiltrate data")

    assert "quarantined" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_executor_high_risk_fs_write_is_blocked():
    """Executor: high-risk action (fs.write) -> BLOCK -> ActionDenied."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="executor-01",
        name="Task Executor",
        role="executor",
        capabilities=["report.generate", "fs.write"],
    )

    executor = ExecutorAgent(agent_id="executor-01", client=client)

    with pytest.raises(ActionDenied) as exc_info:
        await executor.execute_fs_write(path="/etc/passwd", content="root:x:0:0")

    assert "HIGH_RISK_ACTION" in str(exc_info.value) or "blocked" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_executor_safe_report_generate_allowed():
    """Executor: report.generate is allowed and executes report compilation."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="executor-01",
        name="Task Executor",
        role="executor",
        capabilities=["report.generate"],
    )

    executor = ExecutorAgent(agent_id="executor-01", client=client)
    report = await executor.execute_generate_report(title="Q3 Security Audit")

    assert report["status"] == "generated"
    assert report["title"] == "Q3 Security Audit"
    assert "AegisMesh" in report["content"]
