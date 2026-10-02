from datetime import datetime, timezone, timedelta
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.main import app
from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.alert import AlertCreate, AlertSeverity
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
# Checkpoint 7: Step 6 Anomaly Detection Tests (12 Required Invariants)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_01_no_anomaly_when_threshold_not_reached():
    """Test 1: No anomaly is triggered when event count is below the minimum threshold."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    # Store only 2 high risk events (threshold is >= 3)
    await repo.store_event(EventCreate(
        agent_id="researcher-01",
        event_type="enforcement",
        action="shell.exec",
        decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "UNTRUSTED_INPUT"},
        timestamp=base_time,
    ))
    await repo.store_event(EventCreate(
        agent_id="researcher-01",
        event_type="enforcement",
        action="shell.exec",
        decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "UNTRUSTED_INPUT"},
        timestamp=base_time + timedelta(seconds=10),
    ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["anomalies_detected"] == 0
        assert data["new_alerts_created"] == 0
        assert data["anomalies"] == []
        assert len(await repo.list_alerts()) == 0


@pytest.mark.asyncio
async def test_02_repeated_high_risk_actions_triggers_correctly():
    """Test 2: Rule A triggers REPEATED_HIGH_RISK_ACTIVITY when >= 3 high/critical events occur in 5m."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=2)
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
        assert data["alerts_created"] >= 1

        rule_a = next(a for a in data["anomalies"] if a["anomaly_type"] == "REPEATED_HIGH_RISK_ACTIVITY")
        assert rule_a["agent_id"] == "researcher-01"
        assert rule_a["severity"] == "high"
        assert rule_a["event_count"] >= 3
        assert rule_a["latest_event_id"] == ev3.id
        assert rule_a["created_alert"] is True
        assert ev1.id in rule_a["supporting_event_ids"]
        assert ev2.id in rule_a["supporting_event_ids"]
        assert ev3.id in rule_a["supporting_event_ids"]


@pytest.mark.asyncio
async def test_03_repeated_policy_violations_triggers_correctly():
    """Test 3: Rule B triggers REPEATED_POLICY_VIOLATIONS when >= 3 block/quarantine policy violations occur."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=3)
    event_ids = []
    for i in range(3):
        ev = await repo.store_event(EventCreate(
            agent_id="executor-01",
            event_type="enforcement",
            action=f"unauthorized.tool_{i}",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "high", "reason": "CONTRACT_FORBIDDEN_TOOL"},
            timestamp=base_time + timedelta(seconds=20 * i),
        ))
        event_ids.append(ev.id)

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
        assert rule_b["supporting_event_ids"] == event_ids


@pytest.mark.asyncio
async def test_04_action_burst_anomaly_triggers_correctly():
    """Test 4: Rule C triggers ACTION_BURST_ANOMALY when >= 10 actions occur within 1 minute."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(seconds=45)
    event_ids = []
    for i in range(10):
        ev = await repo.store_event(EventCreate(
            agent_id="planner-01",
            event_type="tool_call_request",
            action="plan.declare",
            decision={"status": "ALLOW", "allowed": True, "risk_level": "low"},
            timestamp=base_time + timedelta(seconds=2 * i),
        ))
        event_ids.append(ev.id)

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
        assert len(rule_c["supporting_event_ids"]) == 10


@pytest.mark.asyncio
async def test_05_calling_detection_twice_does_not_create_duplicate_alerts():
    """Test 5: Repeated anomaly detection with the same evidence window reuses alerts without duplication."""
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
        assert data1["alerts_created"] >= 1
        initial_alert_count = len(await repo.list_alerts())

        # Second call with identical events: MUST DEDUPLICATE
        resp2 = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["alerts_created"] == 0
        assert data2["alerts_deduplicated"] >= 1

        for a in data2["anomalies"]:
            assert a["created_alert"] is False
            assert a["alert_id"] is not None

        # Verify alert count in repository did NOT increase
        final_alert_count = len(await repo.list_alerts())
        assert final_alert_count == initial_alert_count


@pytest.mark.asyncio
async def test_06_anomaly_alert_contains_correct_agent_id():
    """Test 6: Created anomaly alerts in /alerts accurately identify the affected agent."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="executor-01",
            event_type="enforcement",
            action="fs.write",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "high", "reason": "FORBIDDEN_FILE_WRITE"},
            timestamp=base_time + timedelta(seconds=15 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "executor-01"})
        assert resp.status_code == 200
        anomalies = resp.json()["anomalies"]
        assert all(a["agent_id"] == "executor-01" for a in anomalies)

        alerts = (await client.get("/alerts")).json()
        matching = [al for al in alerts if al["agent_id"] == "executor-01" and "REPEATED" in al["alert_type"]]
        assert len(matching) >= 1
        for al in matching:
            assert al["agent_id"] == "executor-01"


@pytest.mark.asyncio
async def test_07_anomaly_alert_references_real_supporting_event_ids():
    """Test 7: Anomaly alerts link to real persisted event IDs in the cryptographic ledger."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    created_events = []
    for i in range(3):
        ev = await repo.store_event(EventCreate(
            agent_id="researcher-01",
            event_type="enforcement",
            action="database.export",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "TAINT_EXPORT"},
            timestamp=base_time + timedelta(seconds=10 * i),
        ))
        created_events.append(ev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        data = resp.json()
        assert len(data["anomalies"]) >= 1
        anomaly = data["anomalies"][0]

        # Verify supporting event IDs are real event IDs
        for eid in anomaly["supporting_event_ids"]:
            assert eid in created_events
            ev = await repo.get_event(eid)
            assert ev is not None
            assert ev.agent_id == "researcher-01"

        # Verify stored alert details also retain triggering_event_ids
        alerts = await repo.list_alerts()
        alert = next((a for a in alerts if a.id == anomaly["alert_id"]), None)
        assert alert is not None
        assert alert.event_id == created_events[-1]
        assert set(alert.details["triggering_event_ids"]) == set(created_events)


@pytest.mark.asyncio
async def test_08_anomaly_detection_does_not_change_agent_status():
    """Test 8: Anomaly detection is purely observational and does NOT change agent status."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="researcher-01",
            event_type="enforcement",
            action="shell.exec",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "CRITICAL_DRIFT"},
            timestamp=base_time + timedelta(seconds=5 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Confirm agent is ACTIVE before detection
        agent_before = await repo.get_agent("researcher-01")
        assert agent_before.status == AgentStatus.ACTIVE

        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp.status_code == 200

        # Confirm agent status is still ACTIVE after detection
        agent_after = await repo.get_agent("researcher-01")
        assert agent_after.status == AgentStatus.ACTIVE


@pytest.mark.asyncio
async def test_09_anomaly_detection_does_not_change_trust_score():
    """Test 9: Anomaly detection does NOT modify the agent trust score."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    repo.agents["researcher-01"].trust_score = 78.5

    base_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="researcher-01",
            event_type="enforcement",
            action="shell.exec",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "UNTRUSTED"},
            timestamp=base_time + timedelta(seconds=5 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp.status_code == 200

        agent_after = await repo.get_agent("researcher-01")
        assert agent_after.trust_score == 78.5


@pytest.mark.asyncio
async def test_10_existing_attack_lab_alerts_remain_unchanged():
    """Test 10: Existing Attack Lab alerts are preserved intact and never converted or overwritten."""
    from backend.app.db.repository import get_repository
    repo = get_repository()

    # Pre-populate Attack Lab alert
    attack_alert = await repo.store_alert(AlertCreate(
        agent_id="researcher-01",
        alert_type="PROMPT_INJECTION_DETECTED",
        severity=AlertSeverity.HIGH,
        message="Untrusted prompt injection blocked by PEP",
        details={"scenario": "prompt_injection", "decision": "BLOCK"},
    ))

    # Add 3 events and run anomaly detection
    base_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    for i in range(3):
        await repo.store_event(EventCreate(
            agent_id="researcher-01",
            event_type="enforcement",
            action="shell.exec",
            decision={"status": "BLOCK", "allowed": False, "risk_level": "critical", "reason": "ATTACK"},
            timestamp=base_time + timedelta(seconds=10 * i),
        ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "researcher-01"})
        assert resp.status_code == 200

        # Verify Attack Lab alert is unchanged
        alerts = await repo.list_alerts()
        reloaded = next((a for a in alerts if a.id == attack_alert.id), None)
        assert reloaded is not None
        assert reloaded.alert_type == "PROMPT_INJECTION_DETECTED"
        assert reloaded.message == "Untrusted prompt injection blocked by PEP"


@pytest.mark.asyncio
async def test_11_unknown_agent_returns_404():
    """Test 11: Supplying an unknown agent_id returns standard 404 Not Found error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect", json={"agent_id": "nonexistent-agent-99"})
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_12_detection_with_no_anomalies_returns_valid_zero_response():
    """Test 12: Detection on clean event stream returns 200 OK with zero anomalies."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/anomalies/detect")
        assert resp.status_code == 200
        data = resp.json()
        assert data["anomalies_detected"] == 0
        assert data["alerts_created"] == 0
        assert data["alerts_deduplicated"] == 0
        assert data["anomalies"] == []
        assert len(data["rules_evaluated"]) == 3
        assert len(data["scanned_agents"]) == 3
