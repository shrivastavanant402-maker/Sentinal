"""
Tests for Safe Demo Preparation (scripts/prepare_demo.py).

Verifies:
  1. Without explicit confirmation -> reset does NOT happen.
  2. Protected/production environment -> reset does NOT happen.
  3. Dry-run mode -> previews state without modifying data.
  4. Explicit allowed demo mode -> preparation succeeds.
  5. Running preparation twice is safe/idempotent.
  6. Foundational agents (planner-01, researcher-01, executor-01) remain active with 100.0 trust.
  7. Mission contracts remain available and enabled.
  8. Zero fake events are seeded.
  9. Zero fake alerts are seeded (alert count drops to 0).
  10. Evidence ledger cryptographic hash-chain remains valid.
  11. Normal policy enforcement still works seamlessly after preparation.
"""

import pytest
from datetime import datetime, timezone
import uuid

from backend.app.db.repository import InMemoryRepository
from backend.app.db.repositories.contracts import InMemoryContractRepository
from backend.app.schemas.agent import AgentCreate, AgentStatus
from backend.app.schemas.alert import AlertCreate, AlertSeverity
from backend.app.schemas.event import EventCreate, EventType
from backend.app.schemas.decision import ActionRequest, DecisionStatus
from backend.app.pdp.engine import PolicyDecisionPoint
from backend.app.trust.engine import TrustEngine
from backend.app.ledger.verifier import verify_ledger_chain
from scripts.prepare_demo import (
    prepare_demo,
    check_environment_guard,
    DemoSafetyError,
    FOUNDATIONAL_AGENT_IDS,
    parse_args,
)


@pytest.fixture
def clean_in_memory_environment():
    """Provides an isolated InMemory repository environment for testing demo prep."""
    repo = InMemoryRepository()
    contract_repo = InMemoryContractRepository(seed=True)
    return repo, contract_repo


@pytest.mark.asyncio
async def test_refuses_without_confirmation(clean_in_memory_environment):
    """Test 1: Without explicit confirmation, preparation must fail and mutate nothing."""
    repo, contract_repo = clean_in_memory_environment

    # Seed an alert
    await repo.store_alert(
        AlertCreate(
            agent_id="researcher-01",
            severity=AlertSeverity.HIGH,
            alert_type="POLICY_VIOLATION",
            message="Test violation",
        )
    )

    with pytest.raises(DemoSafetyError, match="Missing explicit confirmation"):
        await prepare_demo(
            confirm_reset=False,
            dry_run=False,
            env_override="development",
            repo_override=repo,
            contract_repo_override=contract_repo,
        )

    # Assert alert was NOT cleared
    alerts = await repo.list_alerts()
    assert len(alerts) == 1


@pytest.mark.asyncio
async def test_refuses_in_production_environment(clean_in_memory_environment):
    """Test 2: In production environment, preparation must be strictly refused."""
    repo, contract_repo = clean_in_memory_environment

    with pytest.raises(DemoSafetyError, match="strictly prohibited in production"):
        await prepare_demo(
            confirm_reset=True,
            dry_run=False,
            env_override="production",
            repo_override=repo,
            contract_repo_override=contract_repo,
        )

    with pytest.raises(DemoSafetyError, match="strictly prohibited in production"):
        check_environment_guard(env_override="prod")


@pytest.mark.asyncio
async def test_dry_run_does_not_modify_data(clean_in_memory_environment):
    """Test 3: Dry run mode reports proposed actions without altering state."""
    repo, contract_repo = clean_in_memory_environment

    # Pre-register degraded agent
    await repo.register_agent(
        AgentCreate(
            id="researcher-01",
            name="Researcher Agent",
            role="researcher",
            capabilities=["web.search"],
        )
    )
    await repo.update_agent_status("researcher-01", AgentStatus.QUARANTINED)

    # Seed alert
    await repo.store_alert(
        AlertCreate(
            agent_id="researcher-01",
            severity=AlertSeverity.CRITICAL,
            alert_type="PROMPT_INJECTION",
            message="Injected payload",
        )
    )

    result = await prepare_demo(
        confirm_reset=False,
        dry_run=True,
        env_override="development",
        repo_override=repo,
        contract_repo_override=contract_repo,
    )

    assert result.dry_run is True
    assert result.success is True
    assert result.alerts_cleared == 1

    # State must be unchanged
    alerts = await repo.list_alerts()
    assert len(alerts) == 1
    agent = await repo.get_agent("researcher-01")
    assert agent.status == AgentStatus.QUARANTINED


@pytest.mark.asyncio
async def test_successful_demo_preparation(clean_in_memory_environment):
    """
    Tests 4, 5, 6, 7, 8, 9:
    In allowed mode with confirmation:
    - Clears transient alerts (0 fake alerts seeded)
    - Resets foundational agents to ACTIVE with 100.0 trust
    - Re-enables mission contracts
    - Preserves ledger validity (0 fake events seeded)
    - Verifies hash chain continuity
    """
    repo, contract_repo = clean_in_memory_environment

    # Create real event in ledger
    ev = await repo.store_event(
        EventCreate(
            agent_id="planner-01",
            event_type=EventType.PLAN_DECLARED,
            action="plan.declare",
            payload={"plan": "Demo objective"},
        )
    )

    # Degrade researcher
    await repo.register_agent(
        AgentCreate(id="researcher-01", name="Researcher", role="researcher")
    )
    await repo.update_agent_status("researcher-01", AgentStatus.QUARANTINED)

    # Seed alert
    await repo.store_alert(
        AlertCreate(
            agent_id="researcher-01",
            event_id=ev.id,
            severity=AlertSeverity.HIGH,
            alert_type="VIOLATION",
            message="Initial test alert",
        )
    )

    # Execute demo preparation
    result = await prepare_demo(
        confirm_reset=True,
        dry_run=False,
        env_override="development",
        repo_override=repo,
        contract_repo_override=contract_repo,
    )

    assert result.success is True
    assert result.dry_run is False
    assert result.alerts_cleared == 1

    # 1. Zero alerts remaining
    remaining_alerts = await repo.list_alerts()
    assert len(remaining_alerts) == 0

    # 2. All 3 foundational agents exist and are ACTIVE with 100.0 trust
    for aid in FOUNDATIONAL_AGENT_IDS:
        agent = await repo.get_agent(aid)
        assert agent is not None, f"Foundational agent {aid} missing"
        assert agent.status == AgentStatus.ACTIVE
        assert agent.trust_score == 100.0

    # 3. Mission contracts are enabled
    for aid in FOUNDATIONAL_AGENT_IDS:
        contract = await contract_repo.get_contract_for_agent(aid)
        assert contract is not None, f"Contract for {aid} missing"
        assert contract.enabled is True

    # 4. Ledger remains valid and only contains genuine past events (no fake events)
    events = await repo.list_events()
    assert len(events) == 1
    assert events[0].id == ev.id
    report = verify_ledger_chain([e.model_dump() for e in events])
    assert report["chain_valid"] is True
    assert len(report["errors"]) == 0


@pytest.mark.asyncio
async def test_idempotent_demo_preparation(clean_in_memory_environment):
    """Test: Running demo preparation twice produces identical clean state."""
    repo, contract_repo = clean_in_memory_environment

    # First run
    res1 = await prepare_demo(
        confirm_reset=True,
        dry_run=False,
        env_override="development",
        repo_override=repo,
        contract_repo_override=contract_repo,
    )
    assert res1.success is True

    # Second run
    res2 = await prepare_demo(
        confirm_reset=True,
        dry_run=False,
        env_override="development",
        repo_override=repo,
        contract_repo_override=contract_repo,
    )
    assert res2.success is True
    assert res2.alerts_cleared == 0  # Already 0 alerts

    # Agents count is stable (no duplicates)
    agents = await repo.list_agents()
    assert len(agents) == 3

    # Contracts count is stable (no duplicates)
    contracts = await contract_repo.list_contracts()
    assert len(contracts) == 3

    # Ledger remains valid
    events = await repo.list_events()
    report = verify_ledger_chain([e.model_dump() for e in events])
    assert report["chain_valid"] is True


@pytest.mark.asyncio
async def test_enforcement_works_after_preparation(clean_in_memory_environment):
    """Test 10: Normal policy enforcement functions correctly after demo preparation."""
    from backend.app.db.repository import set_repository
    from backend.app.db.repositories.contracts import set_contract_repository
    from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
    from backend.app.api.enforcement import execute_enforcement

    repo, contract_repo = clean_in_memory_environment
    set_repository(repo)
    set_contract_repository(contract_repo)
    set_pdp(PolicyDecisionPoint(contract_repository=contract_repo))

    # Prepare demo state
    await prepare_demo(
        confirm_reset=True,
        dry_run=False,
        env_override="development",
        repo_override=repo,
        contract_repo_override=contract_repo,
    )

    # Allowed action for researcher: web.search
    allow_req = ActionRequest(
        agent_id="researcher-01",
        action="web.search",
        resource="https://example.com",
        payload={"query": "safety research"},
    )
    allow_resp = await execute_enforcement(allow_req)
    assert allow_resp.decision == DecisionStatus.ALLOW

    # Prohibited action for researcher: database.export
    deny_req = ActionRequest(
        agent_id="researcher-01",
        action="database.export",
        resource="db://records",
        payload={},
    )
    deny_resp = await execute_enforcement(deny_req)
    assert deny_resp.decision == DecisionStatus.BLOCK

    # Check ledger records both events and chain remains valid
    events = await repo.list_events()
    assert len(events) == 2
    report = verify_ledger_chain([e.model_dump() for e in events])
    assert report["chain_valid"] is True


def test_cli_parser_options():
    """Verify CLI argument parsing behavior."""
    # Test --dry-run
    args = parse_args(["--dry-run"])
    assert args.dry_run is True
    assert args.confirm_demo_reset is False

    # Test --confirm-demo-reset
    args2 = parse_args(["--confirm-demo-reset"])
    assert args2.dry_run is False
    assert args2.confirm_demo_reset is True

    # Test custom environment
    args3 = parse_args(["--confirm-demo-reset", "--env", "demo"])
    assert args3.env_override == "demo"
