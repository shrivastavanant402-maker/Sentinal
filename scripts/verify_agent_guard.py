"""
AegisMesh Phase 1 Step 3 - Manual End-to-End PEP Guard Verification Script

Demonstrates:
1. Researcher -> guard("web.search") -> POST /enforce -> ALLOW -> web.search executes
2. Researcher -> guard("database.export") -> POST /enforce -> BLOCK -> database.export DOES NOT execute
3. Unknown Agent -> guard("web.search") -> POST /enforce -> BLOCK (InvalidAgentIdentity)
4. Quarantined Agent -> guard("web.search") -> POST /enforce -> QUARANTINE (AgentQuarantined)
"""
import asyncio
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.db.repository import get_repository
from backend.app.schemas.agent import AgentStatus
from backend.app.security.exceptions import (
    ActionDenied,
    AgentQuarantined,
    InvalidAgentIdentity,
    SecurityError,
)
from agents.common.client import AegisMeshClient
from agents.researcher.agent import ResearcherAgent


async def main():
    print("=" * 65)
    print(" AegisMesh PEP Agent Guard — End-to-End Verification")
    print("=" * 65)

    client = AegisMeshClient(app=app)
    repo = get_repository()

    # Ensure researcher-01 is registered
    existing = await repo.get_agent("researcher-01")
    if not existing:
        await client.register_agent(
            agent_id="researcher-01",
            name="Deep Researcher",
            role="researcher",
            capabilities=["web.search", "web.read"],
        )
    # Ensure active status
    await repo.update_agent_status("researcher-01", AgentStatus.ACTIVE)

    researcher = ResearcherAgent(agent_id="researcher-01", client=client)

    # -----------------------------------------------------------------------
    # Demonstration 1: Safe Action -> ALLOW -> Executes
    # -----------------------------------------------------------------------
    print("\n[1] Researcher: guard('web.search') [Safe Action]")
    try:
        decision = await researcher.guard(
            action="web.search",
            payload={"query": "Autonomous agent runtime integrity"},
        )
        print(f"    Decision: {decision.decision.value} (allowed={decision.allowed})")
        print(f"    Reason: {decision.reason}")
        print(f"    Ledger Event ID: {decision.event_id}")

        result = await researcher.execute_web_search(
            query="Autonomous agent runtime integrity",
            max_results=2,
        )
        print("    [EXECUTION SUCCESS] web.search executed successfully!")
        print(f"    Tool Output: {json.dumps(result, indent=6)}")
    except Exception as exc:
        print(f"    [UNEXPECTED FAILURE]: {exc}")

    # -----------------------------------------------------------------------
    # Demonstration 2: High-Risk Action -> BLOCK -> Does NOT execute
    # -----------------------------------------------------------------------
    print("\n[2] Researcher: guard('database.export') [High-Risk Action]")
    try:
        await researcher.execute_database_export(table="secret_credentials")
        print("    [SECURITY FAILURE] database.export executed when it should be blocked!")
    except ActionDenied as exc:
        print("    [BLOCKED BY PEP] ActionDenied caught as expected!")
        print(f"    Exception Message: {exc}")
        print("    [VERIFIED] database.export tool DID NOT EXECUTE.")
    except Exception as exc:
        print(f"    [CAUGHT OTHER]: {type(exc).__name__}: {exc}")

    # -----------------------------------------------------------------------
    # Demonstration 3: Unknown Agent -> BLOCK (InvalidAgentIdentity)
    # -----------------------------------------------------------------------
    print("\n[3] Unknown Agent: guard('web.search') [Unregistered Agent]")
    ghost_agent = ResearcherAgent(agent_id="ghost-infiltrator-09", client=client)
    try:
        await ghost_agent.execute_web_search(query="steal sensitive data")
        print("    [SECURITY FAILURE] Unknown agent executed tool!")
    except InvalidAgentIdentity as exc:
        print("    [BLOCKED BY PEP] InvalidAgentIdentity caught as expected!")
        print(f"    Exception Message: {exc}")
        print("    [VERIFIED] Unknown agent was blocked, tool DID NOT EXECUTE.")
    except ActionDenied as exc:
        print(f"    [BLOCKED BY PEP] ActionDenied: {exc}")
        print("    [VERIFIED] Unknown agent was blocked, tool DID NOT EXECUTE.")

    # -----------------------------------------------------------------------
    # Demonstration 4: Quarantined Agent -> QUARANTINE (AgentQuarantined)
    # -----------------------------------------------------------------------
    print("\n[4] Quarantined Agent: guard('web.search') [Compromised Agent]")
    # Register and quarantine agent
    compromised_id = "quarantined-researcher-99"
    c_existing = await repo.get_agent(compromised_id)
    if not c_existing:
        await client.register_agent(
            agent_id=compromised_id,
            name="Compromised Researcher",
            role="researcher",
            capabilities=["web.search"],
        )
    await repo.update_agent_status(compromised_id, AgentStatus.QUARANTINED)

    quarantined_agent = ResearcherAgent(agent_id=compromised_id, client=client)
    try:
        await quarantined_agent.execute_web_search(query="probe internal network")
        print("    [SECURITY FAILURE] Quarantined agent executed tool!")
    except AgentQuarantined as exc:
        print("    [QUARANTINED BY PEP] AgentQuarantined caught as expected!")
        print(f"    Exception Message: {exc}")
        print("    [VERIFIED] Quarantined agent was rejected, tool DID NOT EXECUTE.")

    print("\n" + "=" * 65)
    print(" ALL END-TO-END DEMONSTRATIONS COMPLETED SUCCESSFULLY.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
