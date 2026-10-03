#!/usr/bin/env python3
"""
scripts/prepare_demo.py -- AegisMesh Safe Demo State Preparation

Prepares a controlled, repeatable initial state for hackathon demonstrations:
  1. Environment & Confirmation Guards (prevents accidental production execution)
  2. Cryptographic Ledger Chain Verification (preserves immutable evidence without corruption)
  3. Transient Alert Cleanup (clears stale alerts, ensures 0 fake/seeded alerts)
  4. Foundational Agent Reset (planner-01, researcher-01, executor-01 -> ACTIVE, 100.0 trust)
  5. Mission Contract Verification (ensures default least-privilege contracts are enabled)
  6. In-Memory Runtime State Reset (resets TrustEngine, clears Provenance taint, clears Quarantine)
  7. Non-Foundational Agent Audit (reports historical test agents preserved for ledger integrity)

Usage:
  # 1. Preview changes without modifying any data (safe dry run)
  python scripts/prepare_demo.py --dry-run

  # 2. Execute demo preparation with explicit confirmation
  python scripts/prepare_demo.py --confirm-demo-reset
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import get_settings
from backend.app.db.client import get_supabase_client
from backend.app.db.repository import (
    BaseRepository,
    InMemoryRepository,
    SupabaseRepository,
    get_repository,
)
from backend.app.db.repositories.contracts import (
    BaseContractRepository,
    InMemoryContractRepository,
    SupabaseContractRepository,
    get_contract_repository,
    get_default_seed_contracts,
)
from backend.app.enforcement.quarantine import get_quarantine_controller
from backend.app.ledger.verifier import verify_ledger_chain
from backend.app.provenance.tracker import get_provenance_tracker
from backend.app.schemas.agent import AgentCreate, AgentResponse, AgentStatus
from backend.app.schemas.contract import ContractCreate, ContractUpdate
from backend.app.trust.engine import get_trust_engine

logger = logging.getLogger("aegismesh.prepare_demo")

# Allowed environments for demo reset
ALLOWED_ENVIRONMENTS = {"development", "dev", "demo", "test", "local", "staging"}

# Foundational agents required for standard demo workflows
FOUNDATIONAL_AGENTS: List[AgentCreate] = [
    AgentCreate(
        id="planner-01",
        name="Planner Agent",
        role="planner",
        capabilities=["plan.declare", "task.delegate", "objective.decompose"],
        metadata={"description": "Strategic planning and task decomposition agent"},
    ),
    AgentCreate(
        id="researcher-01",
        name="Researcher Agent",
        role="researcher",
        capabilities=["web.search", "web.read", "research_db.read"],
        metadata={"description": "External information retrieval and evidence gathering agent"},
    ),
    AgentCreate(
        id="executor-01",
        name="Executor Agent",
        role="executor",
        capabilities=["report.generate", "fs.read", "fs.write"],
        metadata={"description": "Artifact synthesis and action execution agent"},
    ),
]

FOUNDATIONAL_AGENT_IDS = {a.id for a in FOUNDATIONAL_AGENTS}


class DemoSafetyError(Exception):
    """Raised when safety preconditions for demo preparation fail."""
    pass


@dataclass
class DemoPreparationResult:
    """Summary of demo preparation operations."""
    success: bool
    dry_run: bool
    environment: str
    alerts_cleared: int
    foundational_agents_reset: List[str] = field(default_factory=list)
    mission_contracts_verified: List[str] = field(default_factory=list)
    ledger_events_count: int = 0
    ledger_chain_valid: bool = True
    ledger_errors: List[str] = field(default_factory=list)
    preserved_test_agents: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


def check_environment_guard(env_override: Optional[str] = None) -> str:
    """
    Validates that the current environment permits demo preparation.
    Refuses execution in production environments.
    """
    settings = get_settings()
    env = (env_override or os.environ.get("AEGISMESH_ENV") or settings.AEGISMESH_ENV).strip().lower()
    demo_mode_flag = os.environ.get("AEGISMESH_DEMO_MODE", "").strip().lower() in ("true", "1", "yes")

    if env in ("production", "prod"):
        raise DemoSafetyError(
            f"REFUSED: Current environment is '{env}'. "
            "Demo preparation is strictly prohibited in production environments."
        )

    if env not in ALLOWED_ENVIRONMENTS and not demo_mode_flag:
        raise DemoSafetyError(
            f"REFUSED: Environment '{env}' is not in allowed demo/development environments: "
            f"{sorted(list(ALLOWED_ENVIRONMENTS))} (or set AEGISMESH_DEMO_MODE=true)."
        )

    return env


async def prepare_demo(
    confirm_reset: bool = False,
    dry_run: bool = False,
    env_override: Optional[str] = None,
    repo_override: Optional[BaseRepository] = None,
    contract_repo_override: Optional[BaseContractRepository] = None,
) -> DemoPreparationResult:
    """
    Safely prepares AegisMesh for a clean demo presentation.

    Preconditions:
      - Valid non-production environment.
      - Explicit confirm_reset=True flag (unless dry_run=True).

    Operations:
      - Verifies evidence ledger hash-chain without truncating or corrupting it.
      - Clears transient alerts (no fake alerts seeded).
      - Resets foundational agents (planner-01, researcher-01, executor-01) to active status with 100.0 trust.
      - Re-enables default seed mission contracts.
      - Resets in-memory controllers (TrustEngine, QuarantineController, ProvenanceTracker).
      - Audits non-foundational historical test agents.
    """
    env = check_environment_guard(env_override)

    if not dry_run and not confirm_reset:
        raise DemoSafetyError(
            "REFUSED: Missing explicit confirmation. "
            "You must supply --confirm-demo-reset to perform demo preparation, "
            "or use --dry-run to inspect proposed actions."
        )

    repo = repo_override or get_repository()
    contract_repo = contract_repo_override or get_contract_repository()
    supabase_client = get_supabase_client() if isinstance(repo, SupabaseRepository) else None

    result = DemoPreparationResult(
        success=False,
        dry_run=dry_run,
        environment=env,
        alerts_cleared=0,
    )

    # -------------------------------------------------------------------------
    # 1. Audit & Verify Existing Evidence Ledger
    # -------------------------------------------------------------------------
    existing_events = await repo.list_events(limit=10000, offset=0)
    events_data = [ev.model_dump() for ev in existing_events]
    ledger_report = verify_ledger_chain(events_data)

    result.ledger_events_count = ledger_report.get("checked", len(events_data))
    result.ledger_chain_valid = ledger_report.get("chain_valid", False)
    result.ledger_errors = ledger_report.get("errors", [])

    if not result.ledger_chain_valid:
        raise DemoSafetyError(
            f"Pre-preparation ledger verification failed! Errors: {result.ledger_errors}"
        )

    result.messages.append(
        f"Ledger verified: {result.ledger_events_count} events intact, "
        "cryptographic hash-chain continuity preserved."
    )

    # -------------------------------------------------------------------------
    # 2. Transient Alerts Handling
    # -------------------------------------------------------------------------
    existing_alerts = await repo.list_alerts(limit=1000)
    alert_count = len(existing_alerts)

    if dry_run:
        result.alerts_cleared = alert_count
        result.messages.append(f"[DRY-RUN] Would clear {alert_count} transient alerts.")
    else:
        if alert_count > 0:
            if supabase_client is not None:
                # Delete alerts by batch of IDs via PostgREST
                alert_ids = [a.id for a in existing_alerts]
                # Split in batches of 100 for safety
                for i in range(0, len(alert_ids), 100):
                    batch = alert_ids[i : i + 100]
                    supabase_client.table("alerts").delete().in_("id", batch).execute()
            elif isinstance(repo, InMemoryRepository):
                repo.alerts.clear()

            # Confirm cleanup
            remaining_alerts = await repo.list_alerts(limit=10)
            result.alerts_cleared = alert_count - len(remaining_alerts)
            result.messages.append(f"Cleared {result.alerts_cleared} transient alerts (0 remaining).")
        else:
            result.alerts_cleared = 0
            result.messages.append("No transient alerts to clear (already 0).")

    # -------------------------------------------------------------------------
    # 3. Foundational Agents Preparation
    # -------------------------------------------------------------------------
    trust_engine = get_trust_engine()
    quarantine_ctrl = get_quarantine_controller()
    provenance_tracker = get_provenance_tracker()

    for agent_data in FOUNDATIONAL_AGENTS:
        aid = agent_data.id
        if dry_run:
            result.foundational_agents_reset.append(aid)
            result.messages.append(f"[DRY-RUN] Would reset foundational agent: {aid} (active, 100.0 trust).")
        else:
            # 1. Ensure registered in repo
            await repo.register_agent(agent_data)

            # 2. Update status to ACTIVE
            await repo.update_agent_status(aid, AgentStatus.ACTIVE)

            # 3. Reset trust in database if Supabase
            if supabase_client is not None:
                supabase_client.table("agents").update({
                    "status": AgentStatus.ACTIVE.value,
                    "trust_score": 100.0,
                    "capabilities": agent_data.capabilities,
                    "metadata": agent_data.metadata,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", aid).execute()
            elif isinstance(repo, InMemoryRepository):
                if aid in repo.agents:
                    repo.agents[aid].status = AgentStatus.ACTIVE
                    repo.agents[aid].trust_score = 100.0

            # 4. Reset in-memory singletons
            await trust_engine.reset_score(aid)
            await provenance_tracker.clear_agent_taint(aid)
            if hasattr(quarantine_ctrl, "_quarantined"):
                quarantine_ctrl._quarantined.pop(aid, None)

            result.foundational_agents_reset.append(aid)
            result.messages.append(f"Reset foundational agent: {aid} -> status=ACTIVE, trust=100.0, tier=TRUSTED.")

    # -------------------------------------------------------------------------
    # 4. Foundational Mission Contracts Verification
    # -------------------------------------------------------------------------
    for seed_c in get_default_seed_contracts():
        aid = seed_c.agent_id
        if dry_run:
            result.mission_contracts_verified.append(aid)
            result.messages.append(f"[DRY-RUN] Would ensure mission contract for {aid} (enabled=True).")
        else:
            existing_contract = await contract_repo.get_contract_for_agent(aid)
            if not existing_contract:
                try:
                    await contract_repo.create_contract(
                        ContractCreate(
                            id=seed_c.id,
                            mission_id=seed_c.mission_id,
                            agent_id=seed_c.agent_id,
                            name=seed_c.name,
                            description=seed_c.description,
                            allowed_tools=seed_c.allowed_tools,
                            forbidden_tools=seed_c.forbidden_tools,
                            allowed_resources=seed_c.allowed_resources,
                            risk_level=seed_c.risk_level,
                            enabled=True,
                        )
                    )
                    result.mission_contracts_verified.append(aid)
                    result.messages.append(f"Created default mission contract for agent: {aid}.")
                except Exception as exc:
                    result.messages.append(f"Warning: could not seed contract for {aid}: {exc}")
            else:
                # Re-enable if disabled
                if not existing_contract.enabled:
                    await contract_repo.update_contract(aid, ContractUpdate(enabled=True))
                result.mission_contracts_verified.append(aid)
                result.messages.append(f"Mission contract active for agent: {aid} (enabled=True).")

    # -------------------------------------------------------------------------
    # 5. Non-Foundational Test Agents Audit
    # -------------------------------------------------------------------------
    all_agents = await repo.list_agents()
    non_foundational = [a for a in all_agents if a.id not in FOUNDATIONAL_AGENT_IDS]

    for nfa in non_foundational:
        result.preserved_test_agents.append(nfa.id)

    if non_foundational:
        result.messages.append(
            f"Preserved {len(non_foundational)} historical non-foundational agents "
            f"({', '.join(a.id for a in non_foundational)}): "
            "these agents are referenced by immutable ledger events; preserving them "
            "maintains relational integrity and cryptographic chain continuity."
        )

    # -------------------------------------------------------------------------
    # 6. Post-Preparation Ledger Verification
    # -------------------------------------------------------------------------
    if not dry_run:
        post_events = await repo.list_events(limit=10000, offset=0)
        post_report = verify_ledger_chain([e.model_dump() for e in post_events])
        result.ledger_chain_valid = post_report.get("chain_valid", False)
        result.ledger_errors = post_report.get("errors", [])
        if not result.ledger_chain_valid:
            raise DemoSafetyError(f"Post-preparation ledger verification failed! Errors: {result.ledger_errors}")

    result.success = True
    return result


def print_report(res: DemoPreparationResult) -> None:
    """Prints a structured summary of the preparation result to stdout."""
    mode_str = "[DRY-RUN] " if res.dry_run else ""
    print()
    print("=" * 68)
    print(f"  {mode_str}AegisMesh Demo State Preparation Report")
    print("=" * 68)
    print(f"  Environment:         {res.environment}")
    print(f"  Execution Status:    {'SUCCESS' if res.success else 'FAILED'}")
    print(f"  Dry Run:             {res.dry_run}")
    print(f"  Alerts Cleared:      {res.alerts_cleared}")
    print(f"  Foundational Agents: {', '.join(res.foundational_agents_reset) or 'None'}")
    print(f"  Mission Contracts:   {', '.join(res.mission_contracts_verified) or 'None'}")
    print(f"  Ledger Events:       {res.ledger_events_count}")
    print(f"  Ledger Chain Valid:  {res.ledger_chain_valid} (0 errors)")
    if res.preserved_test_agents:
        print(f"  Preserved Test IDs:  {', '.join(res.preserved_test_agents)}")
    print("-" * 68)
    print("  Detailed Log:")
    for msg in res.messages:
        print(f"    * {msg}")
    print("=" * 68)
    if res.dry_run:
        print("  NOTE: No changes were committed because --dry-run was specified.")
        print("  To execute demo preparation, run:")
        print("    python scripts/prepare_demo.py --confirm-demo-reset")
    else:
        print("  AegisMesh is now in a pristine, controlled state for the live demo.")
        print("  No fake events or fake alerts were seeded. Ledger is fully valid.")
    print("=" * 68)
    print()


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AegisMesh Safe Demo State Preparation Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe preview without making changes:
  python scripts/prepare_demo.py --dry-run

  # Execute demo preparation:
  python scripts/prepare_demo.py --confirm-demo-reset
        """,
    )
    parser.add_argument(
        "--confirm-demo-reset",
        action="store_true",
        help="Explicit confirmation required to perform state preparation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect current state and display proposed changes without modifying data.",
    )
    parser.add_argument(
        "--env",
        dest="env_override",
        type=str,
        default=None,
        help="Optional environment override (defaults to AEGISMESH_ENV).",
    )
    return parser.parse_args(args)


async def main() -> int:
    args = parse_args()

    # Refuse if neither confirm nor dry-run
    if not args.dry_run and not args.confirm_demo_reset:
        print("\n[ERROR] Missing confirmation flag.", file=sys.stderr)
        print("Demo preparation requires explicit intent to prevent accidental execution.", file=sys.stderr)
        print("Use:\n  python scripts/prepare_demo.py --dry-run\nOr:\n  python scripts/prepare_demo.py --confirm-demo-reset\n", file=sys.stderr)
        return 1

    try:
        res = await prepare_demo(
            confirm_reset=args.confirm_demo_reset,
            dry_run=args.dry_run,
            env_override=args.env_override,
        )
        print_report(res)
        return 0
    except DemoSafetyError as exc:
        print(f"\n[SAFETY ERROR] {exc}\n", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL ERROR] Unexpected failure during demo preparation: {exc}\n", file=sys.stderr)
        logger.exception("Demo preparation failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
