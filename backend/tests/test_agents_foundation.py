import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository
from agents.planner.agent import PlannerAgent
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent
from agents.common.client import AegisMeshClient


class MockTransportClient(AegisMeshClient):
    """
    Subclass of AegisMeshClient that routes in-process to the FastAPI ASGI app.
    """
    def __init__(self, app):
        super().__init__(base_url="http://test")
        self._app = app

    async def register_agent(self, agent_id, name, role, capabilities=None, metadata=None):
        transport = ASGITransport(app=self._app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            resp = await client.post("/agents/register", json={
                "id": agent_id,
                "name": name,
                "role": role,
                "capabilities": capabilities or [],
                "metadata": metadata or {}
            })
            resp.raise_for_status()
            return resp.json()

    async def emit_event(self, agent_id, event_type, action, payload, session_id=None):
        transport = ASGITransport(app=self._app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            resp = await client.post("/events", json={
                "agent_id": agent_id,
                "event_type": event_type,
                "action": action,
                "payload": payload,
                "session_id": session_id
            })
            resp.raise_for_status()
            return resp.json()


@pytest.fixture(autouse=True)
def setup_repo():
    set_repository(InMemoryRepository())


@pytest.mark.asyncio
async def test_planner_researcher_executor_agents():
    client = MockTransportClient(app)

    planner = PlannerAgent(client=client)
    researcher = ResearcherAgent(client=client)
    executor = ExecutorAgent(client=client)

    # 1. Planner declares plan
    plan_event = await planner.run_step(session_id="session-test")
    assert plan_event["event_type"] == "plan_declared"
    assert plan_event["action"] == "plan.declare"
    assert plan_event["agent_id"] == "planner-01"
    assert "steps" in plan_event["payload"]

    # 2. Researcher calls web.search
    search_event = await researcher.run_step(session_id="session-test")
    assert search_event["event_type"] == "tool_call_request"
    assert search_event["action"] == "web.search"
    assert search_event["agent_id"] == "researcher-01"
    assert search_event["previous_hash"] == plan_event["event_hash"]

    # 3. Executor calls report.generate
    report_event = await executor.run_step(session_id="session-test")
    assert report_event["event_type"] == "tool_call_request"
    assert report_event["action"] == "report.generate"
    assert report_event["agent_id"] == "executor-01"
    assert report_event["previous_hash"] == search_event["event_hash"]
