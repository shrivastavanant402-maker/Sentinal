from datetime import datetime, timezone, timedelta
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.main import app
from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.event import EventCreate


@pytest.fixture(autouse=True)
def setup_test_env():
    """Initializes clean repository with foundational agents."""
    repo = InMemoryRepository()
    set_repository(repo)

    now = datetime.now(timezone.utc)
    repo.agents["planner-01"] = AgentResponse(
        id="planner-01",
        name="Planner Agent",
        role="planner",
        status=AgentStatus.ACTIVE,
        trust_score=100.0,
        capabilities=["plan.declare"],
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
        capabilities=["web.search"],
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
        capabilities=["report.generate"],
        metadata={},
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Anomaly Detection Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rule_a_repeated_high_risk_actions():
    """Rule A: >= 3 high/critical risk events within 5 minutes triggers REPEATED_HIGH_RISK_ACTIVITY."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    # Store 3 high/critical events
    ev1 = await repo.store_event(EventCreate(
        agent_id="researcher-01",
        event_type="enforcement",
        action="shell.exec",
        decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "UNTRUSTED_INJECTION"},
        timestamp=base_time,
    ))
    ev2 = await repo.store_event(EventCreate(
        agent_id="researcher-01",
        event_type="enforcement",
        action="fs.read",
        decision={"status": "ALLOW", "allowed": True, "risk_level": "high", "reason": "SENSITIVE_FS_ACCESS"},
        timestamp=base_time + timedelta(seconds=30),
    ))
    ev3 = await repo.store_event(EventCreate(
        agent_id="researcher-01",
        event_type="enforcement",
        action="database.export",
        decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "TAINT_SENSITIVE_LEAK"},
        timestamp=base_time + timedelta(seconds=60),
    ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["anomalies_detected"] >= 1
        assert data["new_alerts_created"] >= 1

        rule_a = next(a for a in data["anomalies"] if a["anomaly_type"] == "REPEATED_HIGH_RISK_ACTIVITY")
        assert rule_a["agent_id"] == "researcher-01"
        assert rule_a["severity"] == "high"
        assert rule_a["event_count"] >= 3
        assert rule_a["latest_event_id"] == ev3.id
        assert rule_a["created_alert"] is True

        # Check alert in /alerts
        alerts_resp = await client.get("/alerts")
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()
        matching = [a for a in alerts if a["alert_type"] == "REPEATED_HIGH_RISK_ACTIVITY"]
        assert len(matching) == 1
        assert matching[0]["event_id"] == ev3.id
        assert matching[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_rule_b_repeated_policy_violations():
    """Rule B: >= 3 block/quarantine policy violations within 5 minutes triggers REPEATED_POLICY_VIOLATIONS."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=3)
    # Store 3 policy violation events
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="executor-01",
            event_type="enforcement",
            action=f"unauthorized.tool_{i}",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "high", "reason": "CONTRACT_FORBIDDEN_TOOL"},
            timestamp=base_time + timedelta(seconds=20 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "executor-01"})
        assert resp.status_code == 200
        data = resp.json()

        rule_b = next(a for a in data["anomalies"] if a["anomaly_type"] == "REPEATED_POLICY_VIOLATIONS")
        assert rule_b["agent_id"] == "executor-01"
        assert rule_b["severity"] == "high"
        assert rule_b["event_count"] == 3
        assert rule_b["created_alert"] is True

        # Verify alert stored
        alerts_resp = await client.get("/alerts")
        alerts = alerts_resp.json()
        matching = [a for a in alerts if a["alert_type"] == "REPEATED_POLICY_VIOLATIONS"]
        assert len(matching) == 1
        assert matching[0]["agent_id"] == "executor-01"


@pytest.mark.asyncio
async def test_rule_c_action_burst_anomaly():
    """Rule C: >= 10 events within 1 minute triggers ACTION_BURST_ANOMALY."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(seconds=45)
    # Store 10 events within 30 seconds
    for i in range(10):
        await repo.store_event(EventCreate(
            agent_id="planner-01",
            event_type="tool_call_request",
            action="plan.declare",
            decision={"status": "ALLOW", "allowed": True, "risk_level": "low"},
            timestamp=base_time + timedelta(seconds=2 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "planner-01"})
        assert resp.status_code == 200
        data = resp.json()

        rule_c = next(a for a in data["anomalies"] if a["anomaly_type"] == "ACTION_BURST_ANOMALY")
        assert rule_c["agent_id"] == "planner-01"
        assert rule_c["severity"] == "medium"
        assert rule_c["event_count"] == 10
        assert rule_c["created_alert"] is True


@pytest.mark.asyncio
async def test_anomaly_deduplication_prevents_duplicate_alerts():
    """Deduplication: calling detect multiple times does NOT generate duplicate alerts for identical events."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="researcher-01",
            event_type="enforcement",
            action="shell.exec",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "MISSION_DRIFT"},
            timestamp=base_time + timedelta(seconds=10 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call creates alert
        resp1 = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["new_alerts_created"] >= 1
        initial_alert_count = len(await repo.list_alerts())

        # Second call with same events: MUST DEDUPLICATE
        resp2 = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["new_alerts_created"] == 0

        for a in data2["anomalies"]:
            assert a["created_alert"] is False
            assert a["alert_id"] is not None

        # Verify alert count in repository did NOT increase
        final_alert_count = len(await repo.list_alerts())
        assert final_alert_count == initial_alert_count


@pytest.mark.asyncio
async def test_detection_does_not_modify_agent_state_or_trust():
    """Anomaly detection is strictly non-enforcing: does NOT change agent status, PEP or trust."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="researcher-01",
            event_type="enforcement",
            action="shell.exec",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "TEST_REASON"},
            timestamp=base_time + timedelta(seconds=5 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp.status_code == 200

        # Check agent status remains ACTIVE and trust score 100.0
        agent = await repo.get_agent("researcher-01")
        assert agent.status == AgentStatus.ACTIVE
        assert agent.trust_score == 100.0


@pytest.mark.asyncio
async def test_detect_all_agents_and_get_endpoint():
    """Calling POST or GET without agent_id scans all agents system-wide."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        post_resp = await client.post("/anomalies/detect")
        assert post_resp.status_code == 200
        data = post_resp.json()
        assert "planner-01" in data["scanned_agents"]
        assert "researcher-01" in data["scanned_agents"]
        assert "executor-01" in data["scanned_agents"]

        get_resp = await client.get("/anomalies/detect")
        assert get_resp.status_code == 200
        assert get_resp.json()["scanned_agents"] == data["scanned_agents"]
