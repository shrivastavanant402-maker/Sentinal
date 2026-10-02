"""
AegisMesh Foundation End-to-End Verification Script
Runs end-to-end checks against the FastAPI Core and Agent Foundation.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.client import check_supabase_connection
from agents.planner.agent import PlannerAgent
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent
from agents.common.client import AegisMeshClient


class InProcessClient(AegisMeshClient):
    def __init__(self, asgi_app):
        super().__init__(base_url="http://test")
        self._app = asgi_app

    async def register_agent(self, agent_id, name, role, capabilities=None, metadata=None):
        transport = ASGITransport(app=self._app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            resp = await client.post("/agents/register", json={
                "id": agent_id, "name": name, "role": role,
                "capabilities": capabilities or [], "metadata": metadata or {}
            })
            resp.raise_for_status()
            return resp.json()

    async def emit_event(self, agent_id, event_type, action, payload, session_id=None):
        transport = ASGITransport(app=self._app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            resp = await client.post("/events", json={
                "agent_id": agent_id, "event_type": event_type,
                "action": action, "payload": payload, "session_id": session_id
            })
            resp.raise_for_status()
            return resp.json()

    async def verify_ledger(self):
        transport = ASGITransport(app=self._app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            resp = await client.get("/ledger/verify")
            resp.raise_for_status()
            return resp.json()

    async def list_events(self):
        transport = ASGITransport(app=self._app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            resp = await client.get("/events")
            resp.raise_for_status()
            return resp.json()


async def main():
    print("=" * 60)
    print(" AegisMesh Foundation Verification Suite")
    print("=" * 60)

    # 1. Supabase Check
    print("\n[1] Checking Supabase Connectivity:")
    supa = check_supabase_connection()
    print(f"    Supabase Status: {json.dumps(supa, indent=2)}")

    # 2. Health Endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        h_res = await http_client.get("/health")
        print(f"\n[2] Health Endpoint (/health): {h_res.status_code}")
        print(f"    Payload: {h_res.json()}")

    # 3. Agent Foundation
    print("\n[3] Initializing Agents (Planner, Researcher, Executor):")
    client = InProcessClient(app)
    planner = PlannerAgent(client=client)
    researcher = ResearcherAgent(client=client)
    executor = ExecutorAgent(client=client)

    # 4. Emit Events
    print("\n[4] Emitting Event 1: Planner -> plan_declared")
    e1 = await planner.run_step(session_id="foundation-test-01")
    print(f"    Seq: {e1['seq']}, Hash: {e1['event_hash'][:16]}..., PrevHash: {e1['previous_hash'][:16]}...")

    print("\n[5] Emitting Event 2: Researcher -> tool_call_request (web.search)")
    e2 = await researcher.run_step(session_id="foundation-test-01")
    print(f"    Seq: {e2['seq']}, Hash: {e2['event_hash'][:16]}..., PrevHash: {e2['previous_hash'][:16]}...")

    print("\n[6] Emitting Event 3: Executor -> tool_call_request (report.generate)")
    e3 = await executor.run_step(session_id="foundation-test-01")
    print(f"    Seq: {e3['seq']}, Hash: {e3['event_hash'][:16]}..., PrevHash: {e3['previous_hash'][:16]}...")

    # 5. Verify Hash Chain
    print("\n[7] Verifying Cryptographic Ledger Chain (/ledger/verify):")
    v_report = await client.verify_ledger()
    print(f"    Chain Valid: {v_report['chain_valid']}")
    print(f"    Events Checked: {v_report['checked']}")
    print(f"    Errors: {v_report['errors']}")

    # 6. Retrieve Event List
    events = await client.list_events()
    print(f"\n[8] Total Events in Ledger: {len(events)}")
    for ev in events:
        print(f"    - Seq #{ev['seq']} | Agent: {ev['agent_id']} | Type: {ev['event_type']} | Action: {ev['action']}")

    print("\n" + "=" * 60)
    if v_report['chain_valid'] and len(events) >= 3:
        print(" ALL FOUNDATION CHECKS PASSED SUCCESSFULLY.")
    else:
        print(" FOUNDATION CHECKS FAILED.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
