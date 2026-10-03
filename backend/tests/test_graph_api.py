"""
Tests for the Graph Topology API endpoint — /graph/topology

Verifies:
    1. Endpoint returns valid GraphTopology structure
    2. Sentinel core node is always present
    3. Agent nodes include trust, taint, status metadata
    4. Edges are generated for registered agents
    5. Stats aggregation is correct
    6. Inferred delegation edges appear for foundation agents
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app
from backend.app.db.repository import set_repository, InMemoryRepository
from backend.app.trust.engine import set_trust_engine, TrustEngine
from backend.app.provenance.tracker import set_provenance_tracker, ProvenanceTracker
from backend.app.enforcement.quarantine import set_quarantine_controller, QuarantineController
from backend.app.schemas.agent import AgentCreate
from backend.app.schemas.event import EventCreate


@pytest.fixture
def app():
    """Create a fresh test app with clean in-memory state."""
    repo = InMemoryRepository()
    set_repository(repo)
    set_trust_engine(TrustEngine())
    set_provenance_tracker(ProvenanceTracker())
    set_quarantine_controller(QuarantineController())
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_client(client):
    """Seed agents and events before testing graph topology."""
    # Register agents
    for agent_data in [
        {"id": "planner-01", "name": "Planner Agent", "role": "planner",
         "capabilities": ["plan.declare", "task.delegate"]},
        {"id": "researcher-01", "name": "Researcher Agent", "role": "researcher",
         "capabilities": ["web.search", "web.read"]},
        {"id": "executor-01", "name": "Executor Agent", "role": "executor",
         "capabilities": ["report.generate", "fs.read"]},
    ]:
        await client.post("/agents", json=agent_data)

    # Emit some events
    for evt in [
        {"agent_id": "planner-01", "event_type": "tool_call_request", "action": "task.delegate",
         "payload": {"target_agent": "researcher-01"}, "decision": {"decision": "ALLOW", "risk_level": "low"}},
        {"agent_id": "researcher-01", "event_type": "tool_call_request", "action": "web.search",
         "payload": {}, "decision": {"decision": "ALLOW", "risk_level": "low"}},
        {"agent_id": "researcher-01", "event_type": "enforcement", "action": "database.export",
         "payload": {}, "decision": {"decision": "BLOCK", "risk_level": "critical"}},
        {"agent_id": "executor-01", "event_type": "tool_call_request", "action": "report.generate",
         "payload": {}, "decision": {"decision": "ALLOW", "risk_level": "low"}},
    ]:
        await client.post("/events", json=evt)

    return client


@pytest.mark.anyio
async def test_graph_topology_returns_valid_structure(seeded_client):
    """Test that /graph/topology returns a valid GraphTopology."""
    res = await seeded_client.get("/graph/topology")
    assert res.status_code == 200

    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert "stats" in data
    assert "sentinel_node" in data


@pytest.mark.anyio
async def test_sentinel_core_node_always_present(seeded_client):
    """The sentinel-core hub node is always present and has correct metadata."""
    data = (await seeded_client.get("/graph/topology")).json()
    sentinel = data["sentinel_node"]

    assert sentinel["id"] == "sentinel-core"
    assert sentinel["name"] == "SentinelMesh Core"
    assert sentinel["role"] == "PEP Hub"
    assert sentinel["trust_score"] == 100.0
    assert sentinel["trust_tier"] == "CORE"
    assert sentinel["taint_label"] == "CLEAN"
    assert sentinel["is_quarantined"] is False


@pytest.mark.anyio
async def test_agent_nodes_have_metadata(seeded_client):
    """Agent nodes include trust, taint, status, capabilities."""
    data = (await seeded_client.get("/graph/topology")).json()
    nodes = data["nodes"]

    assert len(nodes) >= 3
    agent_ids = {n["id"] for n in nodes}
    assert "planner-01" in agent_ids
    assert "researcher-01" in agent_ids
    assert "executor-01" in agent_ids

    for node in nodes:
        assert "trust_score" in node
        assert "taint_label" in node
        assert "status" in node
        assert "capabilities" in node
        assert isinstance(node["capabilities"], list)


@pytest.mark.anyio
async def test_edges_include_enforcement(seeded_client):
    """Agents with events have enforcement edges to sentinel-core."""
    data = (await seeded_client.get("/graph/topology")).json()
    edges = data["edges"]

    enforcement_edges = [e for e in edges if e["edge_type"] == "enforcement"]
    assert len(enforcement_edges) >= 1  # At least one agent has events


@pytest.mark.anyio
async def test_inferred_delegation_edges(seeded_client):
    """Foundation agents should have inferred delegation edges."""
    data = (await seeded_client.get("/graph/topology")).json()
    edges = data["edges"]

    delegation_edges = [e for e in edges if e["edge_type"] == "delegation"]
    sources_targets = {(e["source"], e["target"]) for e in delegation_edges}

    # At least planner -> researcher or planner -> executor should exist
    assert ("planner-01", "researcher-01") in sources_targets or \
           ("planner-01", "executor-01") in sources_targets


@pytest.mark.anyio
async def test_stats_are_correct(seeded_client):
    """Stats should reflect the seeded agents and events."""
    data = (await seeded_client.get("/graph/topology")).json()
    stats = data["stats"]

    assert stats["total_agents"] >= 3
    assert stats["total_events"] >= 4
    assert stats["total_edges"] >= 1
    assert stats["blocked_actions"] >= 1  # We emitted one BLOCK event
    assert stats["allowed_actions"] >= 2  # We emitted at least 2 ALLOW events
    assert isinstance(stats["average_trust"], (int, float))
    assert "last_updated" in stats


@pytest.mark.anyio
async def test_empty_graph_returns_valid_response(app):
    """Even with no agents, the endpoint should return valid empty topology."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/graph/topology")
        assert res.status_code == 200
        data = res.json()
        assert data["sentinel_node"]["id"] == "sentinel-core"
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
