import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.config import get_settings
from backend.app.db.repository import InMemoryRepository, set_repository


@pytest.fixture(autouse=True)
def setup_repo():
    set_repository(InMemoryRepository())


@pytest.mark.asyncio
async def test_events_flow_and_hash_chain():
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Emit Event 1
        ev1 = {
            "agent_id": "planner-01",
            "event_type": "plan_declared",
            "action": "plan.declare",
            "payload": {"goal": "Initial Mission"}
        }
        res1 = await client.post("/events", json=ev1)
        assert res1.status_code == 201
        data1 = res1.json()
        assert data1["seq"] == 1
        assert data1["previous_hash"] == settings.LEDGER_GENESIS_PREV_HASH
        assert len(data1["content_hash"]) == 64
        assert len(data1["event_hash"]) == 64

        # 2. Emit Event 2
        ev2 = {
            "agent_id": "researcher-01",
            "event_type": "tool_call_request",
            "action": "web.search",
            "payload": {"query": "Vulnerability research"}
        }
        res2 = await client.post("/events", json=ev2)
        assert res2.status_code == 201
        data2 = res2.json()
        assert data2["seq"] == 2
        # Hash chain linkage check!
        assert data2["previous_hash"] == data1["event_hash"]

        # 3. Emit Event 3
        ev3 = {
            "agent_id": "executor-01",
            "event_type": "tool_call_request",
            "action": "report.generate",
            "payload": {"title": "Executive Summary"}
        }
        res3 = await client.post("/events", json=ev3)
        assert res3.status_code == 201
        data3 = res3.json()
        assert data3["seq"] == 3
        assert data3["previous_hash"] == data2["event_hash"]

        # 4. Verify Ledger Endpoint
        verify_res = await client.get("/ledger/verify")
        assert verify_res.status_code == 200
        report = verify_res.json()
        assert report["ok"] is True
        assert report["checked"] == 3
        assert report["chain_valid"] is True
        assert len(report["errors"]) == 0
        assert report["latest_hash"] == data3["event_hash"]
