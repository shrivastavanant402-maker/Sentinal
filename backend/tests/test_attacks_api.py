from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.contracts.validator import MissionContractValidator
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    set_contract_repository,
)
from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.main import app
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.policy.evaluator import RuntimePolicyEvaluator
from backend.app.schemas.agent import AgentCreate, AgentResponse, AgentStatus
from backend.app.schemas.contract import ContractCreate
from backend.app.schemas.decision import DecisionStatus, RiskLevel
from backend.app.schemas.event import EventCreate


@pytest.fixture(autouse=True)
def setup_test_env():
    """Initializes clean repository, contract repository, and PDP with seed agents."""
    repo = InMemoryRepository()
    set_repository(repo)

    contract_repo = InMemoryContractRepository(seed=True)
    set_contract_repository(contract_repo)

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        contract_validator=MissionContractValidator(),
        policy_evaluator=RuntimePolicyEvaluator(),
    )
    set_pdp(pdp)

    now = datetime.now(timezone.utc)
    repo.agents["planner-01"] = AgentResponse(
        id="planner-01",
        name="Planner Agent",
        role="planner",
        status=AgentStatus.ACTIVE,
        trust_score=100.0,
        capabilities=["plan.declare", "task.delegate", "objective.decompose"],
        metadata={},
        created_at=now,
        updated_at=now,
    )
    repo.agents["researcher-01"] = AgentResponse(
        id="researcher-01",
        name="Researcher Agent",
        role="researcher",
        status=AgentStatus.ACTIVE,
        trust_score=100.0,
        capabilities=["web.search", "web.read", "research_db.read"],
        metadata={},
        created_at=now,
        updated_at=now,
    )
    repo.agents["executor-01"] = AgentResponse(
        id="executor-01",
        name="Executor Agent",
        role="executor",
        status=AgentStatus.ACTIVE,
        trust_score=100.0,
        capabilities=["report.generate", "fs.read"],
        metadata={},
        created_at=now,
        updated_at=now,
    )
    repo.agents["ide-agent-01"] = AgentResponse(
        id="ide-agent-01",
        name="VS Code IDE Sentinel",
        role="ide_sentinel",
        status=AgentStatus.ACTIVE,
        trust_score=100.0,
        capabilities=["shell.exec", "fs.read", "fs.write", "code.analyze"],
        metadata={"description": "VS Code developer assistant and workspace execution sentinel"},
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_injection_produces_real_decision_and_ledger_event():
    """1. prompt_injection produces real enforcement decision and ledger event."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/attacks/simulate", json={
            "agent_id": "researcher-01",
            "scenario": "prompt_injection"
        })

    assert resp.status_code == 200
    body = resp.json()

    assert body["scenario"] == "prompt_injection"
    assert body["agent_id"] == "researcher-01"
    assert body["decision"] == DecisionStatus.BLOCK.value
    assert body["allowed"] is False
    assert body["risk_level"] in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
    assert body["action"] == "shell.exec"
    assert body["event_id"] is not None
    assert body["status"] == "completed"
    assert body["trust_delta"] is None

    # Verify real event in the ledger repository
    repo = InMemoryRepository()
    from backend.app.db.repository import get_repository
    active_repo = get_repository()
    event = await active_repo.get_event(body["event_id"])
    assert event is not None
    assert event.event_type == "enforcement"
    assert event.action == "shell.exec"
    assert event.decision["status"] == "BLOCK"
    assert event.decision["allowed"] is False


@pytest.mark.asyncio
async def test_secret_exfiltration_produces_real_decision_and_ledger_event():
    """2. secret_exfiltration produces real enforcement decision and ledger event."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/attacks/simulate", json={
            "agent_id": "executor-01",
            "scenario": "secret_exfiltration"
        })

    assert resp.status_code == 200
    body = resp.json()

    assert body["scenario"] == "secret_exfiltration"
    assert body["agent_id"] == "executor-01"
    assert body["decision"] == DecisionStatus.BLOCK.value
    assert body["allowed"] is False
    assert body["risk_level"] in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
    assert body["action"] == "database.export"
    assert body["event_id"] is not None

    # Verify event payload in ledger
    from backend.app.db.repository import get_repository
    active_repo = get_repository()
    event = await active_repo.get_event(body["event_id"])
    assert event is not None
    assert event.action == "database.export"
    assert event.payload["requested_payload"]["target"] == "api_keys.env"


@pytest.mark.asyncio
async def test_rogue_agent_produces_quarantine_through_existing_path():
    """3. rogue_agent produces QUARANTINE through the existing quarantine path."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/attacks/simulate", json={
            "agent_id": "planner-01",
            "scenario": "rogue_agent"
        })

    assert resp.status_code == 200
    body = resp.json()

    assert body["scenario"] == "rogue_agent"
    assert body["agent_id"] == "planner-01"
    assert body["decision"] == DecisionStatus.QUARANTINE.value
    assert body["allowed"] is False
    assert body["reason"] == "AGENT_QUARANTINED"
    assert body["risk_level"] == RiskLevel.CRITICAL.value
    assert "Quarantined" in body["enforcement_outcome"]
    assert body["event_id"] is not None

    # Verify agent state in repo is actually QUARANTINED
    from backend.app.db.repository import get_repository
    active_repo = get_repository()
    agent = await active_repo.get_agent("planner-01")
    assert agent is not None
    assert agent.status == AgentStatus.QUARANTINED


@pytest.mark.asyncio
async def test_blocked_and_quarantined_attacks_create_exactly_one_linked_alert():
    """4. blocked/quarantined attacks create exactly one linked alert."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Run prompt_injection (blocked)
        resp1 = await client.post("/attacks/simulate", json={
            "agent_id": "researcher-01",
            "scenario": "prompt_injection"
        })
        body1 = resp1.json()
        assert body1["alert"] is not None
        assert body1["alert"]["event_id"] == body1["event_id"]
        assert body1["alert"]["agent_id"] == "researcher-01"
        assert body1["alert"]["severity"] in ("high", "critical")
        assert body1["alert"]["alert_type"] == "PROMPT_INJECTION_DETECTED"

        # Verify exactly 1 alert exists in repo so far
        from backend.app.db.repository import get_repository
        active_repo = get_repository()
        alerts1 = await active_repo.list_alerts()
        assert len(alerts1) == 1
        assert alerts1[0].id == body1["alert"]["id"]

        # 2. Run rogue_agent (quarantined)
        resp2 = await client.post("/attacks/simulate", json={
            "agent_id": "executor-01",
            "scenario": "rogue_agent"
        })
        body2 = resp2.json()
        assert body2["alert"] is not None
        assert body2["alert"]["event_id"] == body2["event_id"]
        assert body2["alert"]["severity"] == "critical"
        assert body2["alert"]["alert_type"] == "ROGUE_AGENT_QUARANTINED"

        # Verify exactly 2 alerts exist in total (one per blocked/quarantined attack)
        alerts2 = await active_repo.list_alerts()
        assert len(alerts2) == 2


@pytest.mark.asyncio
async def test_allowed_result_does_not_create_attack_alert():
    """5. allowed result does not create an attack alert."""
    # Register an agent with a contract that explicitly allows shell.exec
    from backend.app.db.repositories.contracts import get_contract_repository
    from backend.app.db.repository import get_repository

    active_repo = get_repository()
    contract_repo = get_contract_repository()

    await active_repo.register_agent(
        AgentCreate(
            id="permissive-agent-01",
            name="Permissive Agent",
            role="admin",
            capabilities=["shell.exec"],
        )
    )

    await contract_repo.create_contract(
        ContractCreate(
            id="contract-permissive",
            mission_id="attack-lab-simulation",
            agent_id="permissive-agent-01",
            name="Permissive Contract",
            description="Allows shell.exec for testing",
            allowed_tools=["shell.exec"],
            forbidden_tools=[],
            risk_level="low",
            enabled=True,
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/attacks/simulate", json={
            "agent_id": "permissive-agent-01",
            "scenario": "prompt_injection"
        })

    assert resp.status_code == 200
    body = resp.json()

    assert body["decision"] == DecisionStatus.ALLOW.value
    assert body["allowed"] is True
    assert body["alert"] is None

    # Verify no alerts were added to the repository
    alerts = await active_repo.list_alerts()
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_unknown_agent_fails_safely():
    """6. unknown agent fails safely via PEP blocking with INVALID_IDENTITY."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/attacks/simulate", json={
            "agent_id": "ghost-agent-99",
            "scenario": "prompt_injection"
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == DecisionStatus.BLOCK.value
    assert body["allowed"] is False
    assert "INVALID_IDENTITY" in str(body["reason"])
    assert body["status"] == "completed"


@pytest.mark.asyncio
async def test_invalid_scenario_is_rejected():
    """7. invalid scenario is rejected with HTTP 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/attacks/simulate", json={
            "agent_id": "researcher-01",
            "scenario": "invalid_ddos_flood"
        })

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ledger_verification_remains_valid_after_attack_simulations():
    """9. ledger verification remains valid across attack simulations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run all three scenarios
        await client.post("/attacks/simulate", json={
            "agent_id": "researcher-01",
            "scenario": "prompt_injection"
        })
        await client.post("/attacks/simulate", json={
            "agent_id": "executor-01",
            "scenario": "secret_exfiltration"
        })
        await client.post("/attacks/simulate", json={
            "agent_id": "planner-01",
            "scenario": "rogue_agent"
        })

        # Check ledger verification endpoint
        v_resp = await client.get("/ledger/verify")
        assert v_resp.status_code == 200
        report = v_resp.json()

        assert report["ok"] is True
        assert report["chain_valid"] is True
        assert report["errors"] == []
        assert report["checked"] >= 3


# ---------------------------------------------------------------------------
# Attack Replay Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_replay_existing_enforcement_event():
    """1. Replay an existing enforcement event."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sim_resp = await client.post("/attacks/simulate", json={
            "agent_id": "researcher-01",
            "scenario": "prompt_injection"
        })
        assert sim_resp.status_code == 200
        event_id = sim_resp.json()["event_id"]

        replay_resp = await client.get(f"/attacks/replay/{event_id}")
        assert replay_resp.status_code == 200
        replay_body = replay_resp.json()

        assert replay_body["event_id"] == event_id
        assert replay_body["agent_id"] == "researcher-01"
        assert replay_body["event_type"] == "enforcement"
        assert replay_body["action"] == "shell.exec"
        assert replay_body["decision"] == "BLOCK"
        assert replay_body["allowed"] is False
        assert replay_body["reason"] is not None
        assert replay_body["risk_level"] in ("high", "critical")
        assert replay_body["enforcement_outcome"] == "Blocked by Policy Enforcement Point"
        assert replay_body["ledger"]["event_hash"] is not None
        assert replay_body["ledger"]["chain_valid"] is True


@pytest.mark.asyncio
async def test_replay_event_with_linked_alert():
    """2. Replaying an event with a linked alert returns the alert record."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sim_resp = await client.post("/attacks/simulate", json={
            "agent_id": "researcher-01",
            "scenario": "secret_exfiltration"
        })
        assert sim_resp.status_code == 200
        sim_data = sim_resp.json()
        event_id = sim_data["event_id"]
        expected_alert_id = sim_data["alert"]["id"]

        replay_resp = await client.get(f"/attacks/replay/{event_id}")
        assert replay_resp.status_code == 200
        replay_body = replay_resp.json()

        assert replay_body["alert"] is not None
        assert replay_body["alert"]["id"] == expected_alert_id
        assert replay_body["alert"]["event_id"] == event_id
        assert replay_body["alert"]["alert_type"] == "SECRET_EXFILTRATION_PREVENTED"
        assert replay_body["alert"]["severity"] in ("high", "critical")
        assert "exfiltration" in replay_body["alert"]["message"].lower()


@pytest.mark.asyncio
async def test_replay_event_without_alert():
    """3. Replaying an event without an alert returns alert: null."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    event = await repo.store_event(EventCreate(
        agent_id="planner-01",
        event_type="plan_declared",
        action="plan.declare",
        payload={"goal": "organize research roadmap"},
        decision={"status": "ALLOW", "allowed": True, "reason": "CONTRACT_PERMITTED", "risk_level": "low"},
    ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        replay_resp = await client.get(f"/attacks/replay/{event.id}")
        assert replay_resp.status_code == 200
        replay_body = replay_resp.json()

        assert replay_body["event_id"] == event.id
        assert replay_body["agent_id"] == "planner-01"
        assert replay_body["action"] == "plan.declare"
        assert replay_body["decision"] == "ALLOW"
        assert replay_body["allowed"] is True
        assert replay_body["alert"] is None
        assert replay_body["ledger"]["seq"] == event.seq
        assert replay_body["ledger"]["event_hash"] == event.event_hash


@pytest.mark.asyncio
async def test_replay_unknown_event_id_returns_404():
    """4. Unknown event_id returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/attacks/replay/unknown-uuid-00000000")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_replay_contains_actual_persisted_identifiers():
    """5. Response contains the actual persisted event/alert identifiers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sim_resp = await client.post("/attacks/simulate", json={
            "agent_id": "planner-01",
            "scenario": "rogue_agent"
        })
        assert sim_resp.status_code == 200
        sim_data = sim_resp.json()
        event_id = sim_data["event_id"]
        alert_id = sim_data["alert"]["id"]

        from backend.app.db.repository import get_repository
        repo = get_repository()
        persisted_event = await repo.get_event(event_id)
        assert persisted_event is not None

        replay_resp = await client.get(f"/attacks/replay/{event_id}")
        assert replay_resp.status_code == 200
        replay_body = replay_resp.json()

        assert replay_body["event_id"] == persisted_event.id
        assert replay_body["alert"]["id"] == alert_id
        assert replay_body["alert"]["event_id"] == persisted_event.id
        assert replay_body["ledger"]["event_hash"] == persisted_event.event_hash
        assert replay_body["ledger"]["previous_hash"] == persisted_event.previous_hash
        assert replay_body["ledger"]["content_hash"] == persisted_event.content_hash
        assert replay_body["ledger"]["seq"] == persisted_event.seq


@pytest.mark.asyncio
async def test_replay_extracts_command_and_ide_agent_identity():
    """6. Replay accurately extracts the real user command and IDE agent name."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Submit an enforcement request from ide-agent-01 with a Python command
        enforce_resp = await client.post("/enforce", json={
            "agent_id": "ide-agent-01",
            "action": "shell.exec",
            "payload": {
                "command": "Write a Python Hello World program",
                "source": "vscode"
            }
        })
        assert enforce_resp.status_code == 200
        enforce_data = enforce_resp.json()
        event_id = enforce_data["event_id"]
        assert event_id is not None

        # Replay the event and verify the command and agent identity are surfaced
        replay_resp = await client.get(f"/attacks/replay/{event_id}")
        assert replay_resp.status_code == 200
        replay_data = replay_resp.json()

        assert replay_data["agent_id"] == "ide-agent-01"
        assert replay_data["agent_name"] == "VS Code IDE Sentinel"
        assert replay_data["action"] == "shell.exec"
        assert replay_data["command"] == "Write a Python Hello World program"
        assert replay_data["decision"] == "ALLOW"
        assert replay_data["allowed"] is True
