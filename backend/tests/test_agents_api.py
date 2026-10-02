import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository


@pytest.fixture(autouse=True)
def setup_repo():
    set_repository(InMemoryRepository())


@pytest.mark.asyncio
async def test_register_and_get_agent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register an agent
        agent_data = {
            "id": "custom-agent-01",
            "name": "Custom Agent",
            "role": "specialist",
            "capabilities": ["custom.tool"],
            "metadata": {"env": "test"}
        }
        res = await client.post("/agents/register", json=agent_data)
        assert res.status_code == 201
        created = res.json()
        assert created["id"] == "custom-agent-01"
        assert created["role"] == "specialist"
        assert created["status"] == "active"
        assert created["trust_score"] == 100.0

        # Retrieve the agent
        get_res = await client.get("/agents/custom-agent-01")
        assert get_res.status_code == 200
        retrieved = get_res.json()
        assert retrieved["name"] == "Custom Agent"

        # List agents
        list_res = await client.get("/agents")
        assert list_res.status_code == 200
        agents = list_res.json()
        assert any(a["id"] == "custom-agent-01" for a in agents)
