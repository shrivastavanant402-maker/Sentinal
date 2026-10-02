import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.db.repository import InMemoryRepository, set_repository, get_repository
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    set_contract_repository,
    get_contract_repository,
)
from backend.app.schemas.contract import ContractUpdate
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentStatus
from backend.app.api.missions import ensure_foundational_agents


@pytest.fixture(autouse=True)
def setup_environment():
    """Reset repository, contract repository, and PDP for fresh isolation."""
    repo = InMemoryRepository()
    set_repository(repo)
    set_contract_repository(InMemoryContractRepository(seed=True))
    set_pdp(PolicyDecisionPoint())


@pytest.mark.asyncio
async def test_missions_run_happy_path():
    """1. POST /missions/run happy path: All agents allowed in sequence."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/missions/run", json={"goal": "Investigate zero-day exploit patterns"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "COMPLETED"
        assert data["goal"] == "Investigate zero-day exploit patterns"
        assert data["mission_id"] is not None
        assert data["session_id"] is not None
        assert data["error"] is None

        # Planner completed
        assert data["planner_result"] is not None
        assert data["planner_result"]["status"] == "delegated"
        assert data["planner_result"]["target_agent"] == "researcher-01"

        # Researcher completed
        assert data["researcher_result"] is not None
        assert data["researcher_result"]["status"] == "success"
        assert len(data["researcher_result"]["results"]) > 0

        # Executor completed
        assert data["executor_result"] is not None
        assert data["executor_result"]["status"] == "generated"
        assert "AegisMesh" in data["executor_result"]["content"]

        # Execution trace has 3 steps, all ALLOW
        assert len(data["execution_trace"]) == 3
        for step in data["execution_trace"]:
            assert step["status"] == "ALLOW"
            assert step["decision"] == "ALLOW"

        # Also verify API v1 prefix works identically
        resp_v1 = await ac.post("/api/v1/missions/run", json={"goal": "Verify v1 endpoint"})
        assert resp_v1.status_code == 200
        assert resp_v1.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_missions_run_planner_blocked():
    """2. Planner blocked: task.delegate not permitted -> mission halts at step 1."""
    await ensure_foundational_agents()
    contract_repo = get_contract_repository()
    # Restrict planner to only plan.declare, forbidding task.delegate
    await contract_repo.update_contract("planner-01", ContractUpdate(allowed_tools=["plan.declare"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/missions/run", json={"goal": "Test planner containment"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "BLOCKED"
        assert data["error"] is not None
        assert data["planner_result"] is None
        assert data["researcher_result"] is None
        assert data["executor_result"] is None

        # Exactly 1 step in trace, showing BLOCKED
        assert len(data["execution_trace"]) == 1
        assert data["execution_trace"][0]["agent_id"] == "planner-01"
        assert data["execution_trace"][0]["action"] == "task.delegate"
        assert data["execution_trace"][0]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_missions_run_researcher_blocked():
    """3. Researcher blocked: web.search not permitted -> mission halts at step 2."""
    await ensure_foundational_agents()
    contract_repo = get_contract_repository()
    # Restrict researcher to only web.read, forbidding web.search
    await contract_repo.update_contract("researcher-01", ContractUpdate(allowed_tools=["web.read"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/missions/run", json={"goal": "Test researcher containment"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "BLOCKED"
        assert data["planner_result"] is not None
        assert data["researcher_result"] is None
        assert data["executor_result"] is None

        # Trace contains step 1 (ALLOW) and step 2 (BLOCKED). Step 3 NEVER executed.
        assert len(data["execution_trace"]) == 2
        assert data["execution_trace"][0]["status"] == "ALLOW"
        assert data["execution_trace"][1]["agent_id"] == "researcher-01"
        assert data["execution_trace"][1]["action"] == "web.search"
        assert data["execution_trace"][1]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_missions_run_executor_blocked():
    """4. Executor blocked: report.generate not permitted -> mission halts at step 3."""
    await ensure_foundational_agents()
    contract_repo = get_contract_repository()
    # Restrict executor to only fs.read, forbidding report.generate
    await contract_repo.update_contract("executor-01", ContractUpdate(allowed_tools=["fs.read"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/missions/run", json={"goal": "Test executor containment"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "BLOCKED"
        assert data["planner_result"] is not None
        assert data["researcher_result"] is not None
        assert data["executor_result"] is None

        # Trace contains step 1 (ALLOW), step 2 (ALLOW), step 3 (BLOCKED)
        assert len(data["execution_trace"]) == 3
        assert data["execution_trace"][0]["status"] == "ALLOW"
        assert data["execution_trace"][1]["status"] == "ALLOW"
        assert data["execution_trace"][2]["agent_id"] == "executor-01"
        assert data["execution_trace"][2]["action"] == "report.generate"
        assert data["execution_trace"][2]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_missions_run_quarantined_agent():
    """5. Quarantined agent halts mission immediately."""
    await ensure_foundational_agents()
    repo = get_repository()
    await repo.update_agent_status("planner-01", AgentStatus.QUARANTINED)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/missions/run", json={"goal": "Test quarantined agent"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "QUARANTINED"
        assert "quarantined" in str(data["error"]).lower()
        assert len(data["execution_trace"]) == 1
        assert data["execution_trace"][0]["status"] == "QUARANTINED"
        assert data["researcher_result"] is None
        assert data["executor_result"] is None


@pytest.mark.asyncio
async def test_missions_run_response_contains_real_event_ids():
    """6. Response contains real, non-empty event IDs matching trace entries."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/missions/run", json={"goal": "Verify event IDs"})
        assert resp.status_code == 200
        data = resp.json()

        event_ids = data["event_ids"]
        assert len(event_ids) == 3

        # Every step in execution_trace has matching event_id
        for i, step in enumerate(data["execution_trace"]):
            eid = step.get("event_id")
            assert eid is not None and len(eid) > 0
            assert eid == event_ids[i]


@pytest.mark.asyncio
async def test_ledger_contains_mission_enforcement_events():
    """7. Ledger contains the mission's enforcement events matching captured event IDs."""
    repo = get_repository()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/missions/run",
            json={"goal": "Verify ledger audit persistence", "mission_id": "mission-ledger-test-99"},
        )
        assert resp.status_code == 200
        data = resp.json()

        returned_event_ids = set(data["event_ids"])
        assert len(returned_event_ids) == 3

        # Verify all events exist in repository / ledger
        stored_events = await repo.list_events()
        stored_ids = {e.id for e in stored_events}

        for eid in returned_event_ids:
            assert eid in stored_ids, f"Event {eid} not found in repository ledger"

        # Verify actions and mission_id
        mission_events = [e for e in stored_events if e.id in returned_event_ids]
        actions = {e.action for e in mission_events}
        assert actions == {"task.delegate", "web.search", "report.generate"}

        for e in mission_events:
            assert e.payload.get("mission_id") == "mission-ledger-test-99"
