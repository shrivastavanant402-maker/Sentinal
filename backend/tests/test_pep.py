import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentCreate, AgentStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_repo_and_pdp():
    """Each test gets a clean in-memory repository and a fresh default PDP."""
    repo = InMemoryRepository()
    set_repository(repo)
    set_pdp(PolicyDecisionPoint())


# ---------------------------------------------------------------------------
# Helper — make HTTP calls through the ASGI app
# ---------------------------------------------------------------------------

async def post_enforce(client: AsyncClient, payload: dict) -> tuple[int, dict]:
    resp = await client.post("/enforce", json=payload)
    return resp.status_code, resp.json()


async def register(client: AsyncClient, agent_id: str, role: str = "researcher"):
    resp = await client.post("/agents/register", json={
        "id": agent_id,
        "name": agent_id.replace("-", " ").title(),
        "role": role,
        "capabilities": ["web.search", "web.read"],
        "metadata": {}
    })
    assert resp.status_code == 201
    return resp.json()


async def set_agent_status(client: AsyncClient, agent_id: str, status: str):
    resp = await client.patch(f"/agents/{agent_id}/status", json={"status": status})
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_known_active_agent_safe_action_allows():
    """Registered active agent + low-risk action → ALLOW, allowed=True."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "researcher-01")

        code, body = await post_enforce(client, {
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "CVEs"}
        })

    assert code == 200
    assert body["decision"] == "ALLOW"
    assert body["allowed"] is True
    assert body["agent_id"] == "researcher-01"
    assert body["action"] == "web.search"


@pytest.mark.asyncio
async def test_unknown_agent_is_blocked():
    """Unregistered agent → BLOCK, allowed=False."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        code, body = await post_enforce(client, {
            "agent_id": "ghost-agent-99",
            "action": "web.search",
            "payload": {}
        })

    assert code == 200
    assert body["decision"] == "BLOCK"
    assert body["allowed"] is False
    assert "INVALID_IDENTITY" in body["reason"]


@pytest.mark.asyncio
async def test_quarantined_agent_is_quarantined():
    """Quarantined agent → QUARANTINE, allowed=False."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "bad-agent-01")
        await set_agent_status(client, "bad-agent-01", "quarantined")

        code, body = await post_enforce(client, {
            "agent_id": "bad-agent-01",
            "action": "web.search",
            "payload": {}
        })

    assert code == 200
    assert body["decision"] == "QUARANTINE"
    assert body["allowed"] is False
    assert "AGENT_QUARANTINED" in body["reason"]


@pytest.mark.asyncio
async def test_high_risk_action_is_blocked():
    """Known active agent + explicitly high-risk action → BLOCK, allowed=False."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "executor-01", role="executor")

        code, body = await post_enforce(client, {
            "agent_id": "executor-01",
            "action": "database.export",
            "payload": {"table": "customers"}
        })

    assert code == 200
    assert body["decision"] == "BLOCK"
    assert body["allowed"] is False
    # Phase 2: drift detector runs before risk classifier — MISSION_DRIFT is now
    # the primary reason when the action is in forbidden_tools; HIGH_RISK_ACTION
    # is the Phase 1 reason; TAINT_SENSITIVE_LEAK is the taint sink reason.
    assert body["reason"] in ("HIGH_RISK_ACTION", "MISSION_DRIFT", "CONTRACT_VIOLATION", "TAINT_SENSITIVE_LEAK")
    assert body["risk_level"] in ("high", "critical")


@pytest.mark.asyncio
async def test_enforcement_event_written_to_ledger():
    """POST /enforce must write a tamper-proof event to the ledger."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "researcher-01")

        code, body = await post_enforce(client, {
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "test"}
        })

        assert code == 200
        assert body["event_id"] is not None

        # The event must exist in the ledger
        ev_resp = await client.get(f"/events/{body['event_id']}")
        assert ev_resp.status_code == 200
        event = ev_resp.json()

        assert event["event_type"] == "enforcement"
        assert event["agent_id"] == "researcher-01"
        assert event["action"] == "web.search"


@pytest.mark.asyncio
async def test_enforcement_event_includes_decision():
    """The stored enforcement event must contain the decision in its payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "researcher-01")

        _, body = await post_enforce(client, {
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "test"}
        })

        ev_resp = await client.get(f"/events/{body['event_id']}")
        event = ev_resp.json()

    decision = event["decision"]
    assert decision["status"] == "ALLOW"
    assert decision["allowed"] is True
    assert "reason" in decision
    assert "risk_level" in decision


@pytest.mark.asyncio
async def test_enforcement_event_passes_ledger_verification():
    """After enforcement, the ledger chain must remain mathematically valid."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "researcher-01")

        await post_enforce(client, {
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "integrity check"}
        })

        verify_resp = await client.get("/ledger/verify")
        assert verify_resp.status_code == 200
        report = verify_resp.json()

    assert report["ok"] is True
    assert report["chain_valid"] is True
    assert report["errors"] == []


@pytest.mark.asyncio
async def test_block_does_not_execute_action():
    """BLOCK must return the decision without side effects.
    The only artefact must be one ledger event."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        code, body = await post_enforce(client, {
            "agent_id": "unknown-99",
            "action": "database.export",
            "payload": {"table": "secrets"}
        })

    # Correctly formed HTTP response
    assert code == 200
    assert body["decision"] == "BLOCK"
    assert body["allowed"] is False
    # event_id is set (ledger recorded the block)
    assert body["event_id"] is not None


@pytest.mark.asyncio
async def test_enforce_correct_http_schema():
    """Enforce endpoint returns valid DecisionResponse schema for all fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "planner-01", role="planner")

        code, body = await post_enforce(client, {
            "agent_id": "planner-01",
            "action": "plan.declare",
            "payload": {"goal": "test"},
            "session_id": "sess-42"
        })

    assert code == 200
    # All required DecisionResponse fields present
    for field in ("decision", "allowed", "reason", "risk_level", "agent_id", "action", "details"):
        assert field in body, f"Missing field: {field}"
    assert body["agent_id"] == "planner-01"
    assert body["action"] == "plan.declare"


@pytest.mark.asyncio
async def test_different_decisions_produce_different_hashes():
    """Two enforcement events with different decisions must have different content hashes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register(client, "researcher-01")

        # ALLOW event
        _, allow_body = await post_enforce(client, {
            "agent_id": "researcher-01",
            "action": "web.search",
            "payload": {"query": "test"}
        })
        # BLOCK event (unknown agent)
        _, block_body = await post_enforce(client, {
            "agent_id": "unknown-ghost",
            "action": "web.search",
            "payload": {"query": "test"}
        })

        allow_ev = (await client.get(f"/events/{allow_body['event_id']}")).json()
        block_ev = (await client.get(f"/events/{block_body['event_id']}")).json()

    assert allow_ev["content_hash"] != block_ev["content_hash"]
    assert allow_ev["event_hash"] != block_ev["event_hash"]


@pytest.mark.asyncio
async def test_malformed_request_returns_422():
    """Missing required fields must return HTTP 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/enforce", json={"agent_id": "researcher-01"})  # missing action

    assert resp.status_code == 422
