"""
Phase 2 Tests — Trust Engine, Provenance/Taint Tracker, Mission Drift Detector,
Quarantine Controller, and PDP Phase 2 Integration.

Tests: 28 total
    test_trust_*            (8)
    test_provenance_*       (7)
    test_drift_*            (7)
    test_quarantine_*       (3)
    test_pdp_phase2_*       (3)
"""

import pytest
import pytest_asyncio

from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentCreate, AgentStatus
from backend.app.schemas.decision import ActionRequest, DecisionStatus, RiskLevel
from backend.app.schemas.contract import MissionContract, ContractCreate
from backend.app.db.repositories.contracts import InMemoryContractRepository, set_contract_repository
from backend.app.trust.engine import TrustEngine, TrustTier, set_trust_engine
from backend.app.provenance.tracker import (
    ProvenanceTracker, TaintLabel, set_provenance_tracker
)
from backend.app.drift.detector import DriftDetector, DriftSeverity, set_drift_detector
from backend.app.enforcement.quarantine import (
    QuarantineController, QUARANTINE_TRUST_THRESHOLD, set_quarantine_controller
)


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


@pytest.fixture
def contract_repo():
    cr = InMemoryContractRepository()
    set_contract_repository(cr)
    return cr


@pytest.fixture
def trust_engine():
    engine = TrustEngine()
    set_trust_engine(engine)
    return engine


@pytest.fixture
def provenance_tracker():
    tracker = ProvenanceTracker()
    set_provenance_tracker(tracker)
    return tracker


@pytest.fixture
def drift_detector():
    detector = DriftDetector()
    set_drift_detector(detector)
    return detector


@pytest.fixture
def quarantine_controller(repo):
    qc = QuarantineController(repository=repo)
    set_quarantine_controller(qc)
    return qc


@pytest_asyncio.fixture
async def registered_agent(repo):
    """Registers test-agent-01 in the repository."""
    agent = await repo.register_agent(AgentCreate(
        id="test-agent-01",
        name="Test Agent",
        role="researcher",
        capabilities=["web.search"],
    ))
    return agent


@pytest.fixture
def researcher_contract():
    return MissionContract(
        id="contract-researcher-test",
        agent_id="test-agent-01",
        name="Researcher Contract",
        description="Research only contract",
        allowed_tools=["web.search", "web.read", "research_db.read"],
        forbidden_tools=["database.export", "external.post", "shell.exec"],
        risk_level=RiskLevel.MEDIUM,
        enabled=True,
    )


# ===========================================================================
# TRUST ENGINE TESTS (8)
# ===========================================================================

@pytest.mark.asyncio
async def test_trust_initial_score_is_100(trust_engine):
    """A new agent starts with composite trust of 100."""
    score = await trust_engine.get_score("agent-new")
    assert score.composite == 100.0
    assert score.tier == TrustTier.TRUSTED


@pytest.mark.asyncio
async def test_trust_allow_decision_no_penalty(trust_engine):
    """ALLOW decisions do not reduce trust score."""
    score = await trust_engine.apply_decision("agent-01", DecisionStatus.ALLOW, RiskLevel.LOW)
    assert score.composite == 100.0
    assert score.consecutive_clean == 1


@pytest.mark.asyncio
async def test_trust_block_low_risk_penalty(trust_engine):
    """BLOCK with LOW risk deducts 5 from compliance dimension."""
    score = await trust_engine.apply_decision("agent-02", DecisionStatus.BLOCK, RiskLevel.LOW)
    # compliance = 100 - 5 = 95
    expected = 0.35 * 95 + 0.25 * 100 + 0.20 * 100 + 0.20 * 100
    assert abs(score.composite - expected) < 0.01


@pytest.mark.asyncio
async def test_trust_block_critical_risk_penalty(trust_engine):
    """BLOCK with CRITICAL risk deducts 50 from compliance dimension."""
    score = await trust_engine.apply_decision("agent-03", DecisionStatus.BLOCK, RiskLevel.CRITICAL)
    # compliance = 100 - 50 = 50
    expected = 0.35 * 50 + 0.25 * 100 + 0.20 * 100 + 0.20 * 100
    assert abs(score.composite - expected) < 0.01
    assert score.violations == 1
    assert score.consecutive_clean == 0


@pytest.mark.asyncio
async def test_trust_tier_transitions(trust_engine):
    """Trust tiers transition correctly when penalties accumulate."""
    agent_id = "agent-tier-test"
    # Each CRITICAL BLOCK: compliance -50.  After 2 blocks: compliance=0.
    # Need all 4 dimensions to drop.  Apply multiple violations across dimensions.
    for _ in range(2):
        await trust_engine.apply_decision(agent_id, DecisionStatus.BLOCK, RiskLevel.CRITICAL)
    for _ in range(2):
        await trust_engine.apply_integrity_violation(agent_id, RiskLevel.CRITICAL)
    for _ in range(2):
        await trust_engine.apply_consistency_violation(agent_id, RiskLevel.CRITICAL)
    for _ in range(2):
        await trust_engine.apply_false_claim(agent_id, RiskLevel.CRITICAL)

    score = await trust_engine.get_score(agent_id)
    # All 4 dimensions should be at 0 → composite = 0
    assert score.composite < QUARANTINE_TRUST_THRESHOLD
    assert score.tier == TrustTier.QUARANTINED


@pytest.mark.asyncio
async def test_trust_recovery_on_consecutive_clean(trust_engine):
    """After 10 consecutive clean ALLOW decisions, trust recovers by +1."""
    agent_id = "agent-recovery"
    # Drop compliance
    await trust_engine.apply_decision(agent_id, DecisionStatus.BLOCK, RiskLevel.MEDIUM)
    score_before = await trust_engine.get_score(agent_id)
    composite_before = score_before.composite

    # 10 consecutive ALLOWs → recovery trigger
    for _ in range(10):
        await trust_engine.apply_decision(agent_id, DecisionStatus.ALLOW, RiskLevel.LOW)

    score_after = await trust_engine.get_score(agent_id)
    assert score_after.composite > composite_before


@pytest.mark.asyncio
async def test_trust_integrity_violation_penalty(trust_engine):
    """Integrity violations reduce the integrity dimension."""
    score = await trust_engine.apply_integrity_violation("agent-integrity", RiskLevel.HIGH)
    assert score.integrity == 70.0
    expected = 0.35 * 100 + 0.25 * 70 + 0.20 * 100 + 0.20 * 100
    assert abs(score.composite - expected) < 0.01


@pytest.mark.asyncio
async def test_trust_false_claim_penalty(trust_engine):
    """False claims reduce claim_accuracy dimension."""
    score = await trust_engine.apply_false_claim("agent-claims", RiskLevel.MEDIUM)
    assert score.claim_accuracy == 85.0
    expected = 0.35 * 100 + 0.25 * 100 + 0.20 * 100 + 0.20 * 85
    assert abs(score.composite - expected) < 0.01


# ===========================================================================
# PROVENANCE / TAINT TRACKER TESTS (7)
# ===========================================================================

@pytest.mark.asyncio
async def test_provenance_clean_by_default(provenance_tracker):
    """A fresh agent has no taint."""
    label = await provenance_tracker.get_agent_taint("clean-agent")
    assert label == TaintLabel.CLEAN


@pytest.mark.asyncio
async def test_provenance_mark_tainted(provenance_tracker):
    """Marking an agent tainted sets the SENSITIVE label."""
    await provenance_tracker.mark_tainted("agent-a", source_tool="secrets.read")
    label = await provenance_tracker.get_agent_taint("agent-a")
    assert label == TaintLabel.SENSITIVE


@pytest.mark.asyncio
async def test_provenance_taint_propagation(provenance_tracker):
    """Taint propagates from a tainted sender to a recipient."""
    await provenance_tracker.mark_tainted("sender-agent", source_tool="env.read")
    await provenance_tracker.propagate("sender-agent", "receiver-agent")
    label = await provenance_tracker.get_agent_taint("receiver-agent")
    assert label == TaintLabel.TAINTED


@pytest.mark.asyncio
async def test_provenance_taint_hit_on_sensitive_sink(provenance_tracker):
    """Tainted agent requesting a forbidden sink produces a taint HIT."""
    await provenance_tracker.mark_tainted("exfil-agent", source_tool="secrets.read")
    result = await provenance_tracker.check_sink("exfil-agent", "external.post")
    assert result.is_tainted is True
    assert result.record is not None
    assert result.record.is_hit is True
    assert result.record.sink_tool == "external.post"


@pytest.mark.asyncio
async def test_provenance_no_hit_for_safe_sink(provenance_tracker):
    """Tainted agent requesting a safe action does NOT produce a sink hit."""
    await provenance_tracker.mark_tainted("tainted-agent", source_tool="api_key.read")
    result = await provenance_tracker.check_sink("tainted-agent", "web.search")
    assert result.is_tainted is True
    assert result.record is None  # no hit recorded for safe sink


@pytest.mark.asyncio
async def test_provenance_keyword_detection_in_payload(provenance_tracker):
    """Payload with sensitive keywords flags the agent as UNTRUSTED."""
    result = await provenance_tracker.check_sink(
        "fresh-agent",
        "web.search",
        payload={"api_key": "sk-1234", "query": "redis"},
    )
    assert result.is_tainted is True
    assert result.label == TaintLabel.UNTRUSTED


@pytest.mark.asyncio
async def test_provenance_clear_resets_taint(provenance_tracker):
    """Clearing an agent's taint resets it to CLEAN."""
    await provenance_tracker.mark_tainted("clear-agent", source_tool="token.read")
    await provenance_tracker.clear_agent_taint("clear-agent")
    label = await provenance_tracker.get_agent_taint("clear-agent")
    assert label == TaintLabel.CLEAN


# ===========================================================================
# MISSION DRIFT DETECTOR TESTS (7)
# ===========================================================================

@pytest.mark.asyncio
async def test_drift_allowed_action_is_zero(drift_detector, researcher_contract):
    """An action in the allowlist has 0.0 drift."""
    request = ActionRequest(agent_id="test-agent-01", action="web.search")
    result = drift_detector.evaluate(request, researcher_contract)
    assert result.drift_score == 0.0
    assert result.severity == DriftSeverity.NONE


@pytest.mark.asyncio
async def test_drift_forbidden_action_is_critical(drift_detector, researcher_contract):
    """A forbidden action has drift_score=1.0 and CRITICAL severity."""
    request = ActionRequest(agent_id="test-agent-01", action="database.export")
    result = drift_detector.evaluate(request, researcher_contract)
    assert result.drift_score == 1.0
    assert result.severity == DriftSeverity.CRITICAL


@pytest.mark.asyncio
async def test_drift_unknown_action_is_moderate(drift_detector, researcher_contract):
    """An unknown action (not in allowlist or denylist) is MODERATE drift."""
    request = ActionRequest(agent_id="test-agent-01", action="custom.unknown.tool")
    result = drift_detector.evaluate(request, researcher_contract)
    assert result.severity == DriftSeverity.MODERATE
    assert result.drift_score == 0.5


@pytest.mark.asyncio
async def test_drift_no_contract_is_moderate(drift_detector):
    """Without a contract, drift cannot be evaluated — returns MODERATE."""
    request = ActionRequest(agent_id="test-agent-01", action="web.search")
    result = drift_detector.evaluate(request, None)
    assert result.severity == DriftSeverity.MODERATE


@pytest.mark.asyncio
async def test_drift_risk_envelope_breach(drift_detector):
    """An action with risk higher than contract's max is HIGH drift."""
    contract = MissionContract(
        id="low-risk-contract",
        agent_id="test-agent-01",
        name="Low Risk Only",
        allowed_tools=["web.read"],
        forbidden_tools=[],
        risk_level=RiskLevel.LOW,
        enabled=True,
    )
    # shell.exec is HIGH risk — exceeds LOW contract envelope
    request = ActionRequest(agent_id="test-agent-01", action="shell.exec")
    result = drift_detector.evaluate(request, contract)
    assert result.severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL)
    assert result.drift_score >= 0.7


@pytest.mark.asyncio
async def test_drift_forbidden_has_forbidden_flag(drift_detector, researcher_contract):
    """DriftResult for a forbidden action includes forbidden=True in details."""
    request = ActionRequest(agent_id="test-agent-01", action="shell.exec")
    result = drift_detector.evaluate(request, researcher_contract)
    assert result.details.get("forbidden") is True


@pytest.mark.asyncio
async def test_drift_result_to_dict(drift_detector, researcher_contract):
    """DriftResult.to_dict() produces the correct schema."""
    request = ActionRequest(agent_id="test-agent-01", action="web.search")
    result = drift_detector.evaluate(request, researcher_contract)
    d = result.to_dict()
    assert "drift_score" in d
    assert "severity" in d
    assert "reason" in d
    assert "details" in d


# ===========================================================================
# QUARANTINE CONTROLLER TESTS (3)
# ===========================================================================

@pytest.mark.asyncio
async def test_quarantine_sets_agent_status(quarantine_controller, repo, registered_agent):
    """Quarantining an agent sets its status to QUARANTINED in the repository."""
    result = await quarantine_controller.quarantine_agent(
        agent_id="test-agent-01",
        reason="Test quarantine",
        trigger="test",
    )
    assert result.quarantined is True
    agent = await repo.get_agent("test-agent-01")
    assert agent.status == AgentStatus.QUARANTINED


@pytest.mark.asyncio
async def test_quarantine_release_restores_active(quarantine_controller, repo, registered_agent):
    """Releasing a quarantined agent restores ACTIVE status."""
    await quarantine_controller.quarantine_agent(
        agent_id="test-agent-01",
        reason="Test quarantine",
        trigger="test",
    )
    result = await quarantine_controller.release_agent("test-agent-01", reason="Test release")
    assert result.quarantined is False
    agent = await repo.get_agent("test-agent-01")
    assert agent.status == AgentStatus.ACTIVE


@pytest.mark.asyncio
async def test_auto_quarantine_triggers_below_threshold(quarantine_controller, repo, registered_agent):
    """maybe_quarantine triggers automatically when trust < 40."""
    result = await quarantine_controller.maybe_quarantine(
        agent_id="test-agent-01",
        trust_score=30.0,  # below threshold
    )
    assert result is not None
    assert result.quarantined is True
    assert result.trigger == "trust_score"


@pytest.mark.asyncio
async def test_quarantine_state_persisted_in_repository(quarantine_controller, repo, registered_agent):
    """Quarantine persists in the repository — not just in-memory."""
    await quarantine_controller.quarantine_agent(
        agent_id="test-agent-01",
        reason="Persistence test",
        trigger="test",
    )
    # Verify via repo directly (not through controller cache)
    agent = await repo.get_agent("test-agent-01")
    assert agent.status == AgentStatus.QUARANTINED


@pytest.mark.asyncio
async def test_quarantine_event_is_auditable(quarantine_controller, repo, registered_agent):
    """Quarantine transitions produce ledger events (auditable)."""
    initial_events = await repo.list_events()
    initial_count = len(initial_events)

    await quarantine_controller.quarantine_agent(
        agent_id="test-agent-01",
        reason="Audit test",
        trigger="test",
    )

    events_after = await repo.list_events()
    assert len(events_after) > initial_count
    # The last event should be the quarantine event
    quarantine_event = events_after[-1]
    assert quarantine_event.action == "agent.quarantine"
    assert quarantine_event.agent_id == "test-agent-01"


@pytest.mark.asyncio
async def test_release_event_is_auditable(quarantine_controller, repo, registered_agent):
    """Release transitions produce ledger events (auditable)."""
    await quarantine_controller.quarantine_agent(
        agent_id="test-agent-01",
        reason="Pre-release",
        trigger="test",
    )
    events_before = await repo.list_events()
    before_count = len(events_before)

    await quarantine_controller.release_agent("test-agent-01", reason="Release audit test")

    events_after = await repo.list_events()
    assert len(events_after) > before_count
    release_event = events_after[-1]
    assert release_event.action == "agent.quarantine.release"


@pytest.mark.asyncio
async def test_list_quarantined_reflects_repo_truth(quarantine_controller, repo, registered_agent):
    """list_quarantined returns agents quarantined via any path, not just the controller."""
    # Quarantine directly via repository (bypassing controller cache)
    await repo.update_agent_status("test-agent-01", AgentStatus.QUARANTINED)

    quarantined = await quarantine_controller.list_quarantined()
    assert "test-agent-01" in quarantined


@pytest.mark.asyncio
async def test_trust_cannot_turn_block_into_allow(repo, contract_repo, trust_engine, registered_agent):
    """High trust score cannot override a contract BLOCK into ALLOW."""
    await contract_repo.create_contract(ContractCreate(
        id="c-strict",
        agent_id="test-agent-01",
        name="Strict Contract",
        allowed_tools=["web.search"],
        forbidden_tools=["shell.exec"],
        risk_level=RiskLevel.MEDIUM,
    ))

    fresh_tracker = ProvenanceTracker()
    set_provenance_tracker(fresh_tracker)

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=fresh_tracker,
    )
    set_pdp(pdp)

    # Agent has perfect trust (100) — but shell.exec is forbidden
    request = ActionRequest(agent_id="test-agent-01", action="shell.exec")
    decision = await pdp.evaluate(request, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.allowed is False


@pytest.mark.asyncio
async def test_trust_induced_quarantine_blocks_subsequent_request(
    repo, contract_repo, trust_engine, registered_agent
):
    """After trust drops below quarantine threshold, next PDP evaluation returns QUARANTINE."""
    await contract_repo.create_contract(ContractCreate(
        id="c-boundary",
        agent_id="test-agent-01",
        name="Boundary Contract",
        allowed_tools=["web.search"],
        forbidden_tools=["shell.exec"],
        risk_level=RiskLevel.MEDIUM,
    ))

    fresh_tracker = ProvenanceTracker()
    set_provenance_tracker(fresh_tracker)

    qc = QuarantineController(repository=repo)
    set_quarantine_controller(qc)

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=fresh_tracker,
        quarantine_controller=qc,
    )
    set_pdp(pdp)

    # Hammer trust score down across all dimensions to trigger quarantine
    for _ in range(3):
        await trust_engine.apply_decision("test-agent-01", DecisionStatus.BLOCK, RiskLevel.CRITICAL)
    for _ in range(2):
        await trust_engine.apply_integrity_violation("test-agent-01", RiskLevel.CRITICAL)
    for _ in range(2):
        await trust_engine.apply_consistency_violation("test-agent-01", RiskLevel.CRITICAL)

    score = await trust_engine.get_score("test-agent-01")
    assert score.composite < QUARANTINE_TRUST_THRESHOLD

    # Auto-quarantine via controller
    await qc.maybe_quarantine("test-agent-01", trust_score=score.composite)

    # Refresh agent from repo (status is now QUARANTINED)
    agent = await repo.get_agent("test-agent-01")
    assert agent.status == AgentStatus.QUARANTINED

    # Next request should be QUARANTINE-blocked at the fast-path (step 1 of PDP)
    request = ActionRequest(agent_id="test-agent-01", action="web.search")
    decision = await pdp.evaluate(request, agent=agent)
    assert decision.decision == DecisionStatus.QUARANTINE
    assert decision.allowed is False
    assert decision.reason.value == "AGENT_QUARANTINED"


# ===========================================================================
# PDP PHASE 2 INTEGRATION TESTS (3)
# ===========================================================================

@pytest.mark.asyncio
async def test_pdp_taint_hit_blocks_action(repo, contract_repo, trust_engine, registered_agent):
    """A tainted agent requesting a forbidden sink is BLOCKED by the PDP."""
    await contract_repo.create_contract(ContractCreate(
        id="c-researcher",
        agent_id="test-agent-01",
        name="Researcher",
        allowed_tools=["web.search", "research_db.read"],
        forbidden_tools=["external.post"],
        risk_level=RiskLevel.MEDIUM,
    ))

    tracker = ProvenanceTracker()
    set_provenance_tracker(tracker)
    await tracker.mark_tainted("test-agent-01", source_tool="secrets.read")

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=tracker,
    )
    set_pdp(pdp)

    request = ActionRequest(agent_id="test-agent-01", action="external.post")
    decision = await pdp.evaluate(request, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.reason.value == "TAINT_SENSITIVE_LEAK"
    assert decision.allowed is False


@pytest.mark.asyncio
async def test_pdp_drift_critical_blocks_action(repo, contract_repo, trust_engine, registered_agent):
    """A forbidden action (CRITICAL drift) is BLOCKED by the PDP drift check."""
    await contract_repo.create_contract(ContractCreate(
        id="c-researcher-drift",
        agent_id="test-agent-01",
        name="Researcher",
        allowed_tools=["web.search"],
        forbidden_tools=["shell.exec"],
        risk_level=RiskLevel.MEDIUM,
    ))

    fresh_tracker = ProvenanceTracker()
    set_provenance_tracker(fresh_tracker)

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=fresh_tracker,
    )
    set_pdp(pdp)

    request = ActionRequest(agent_id="test-agent-01", action="shell.exec")
    decision = await pdp.evaluate(request, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.reason.value == "MISSION_DRIFT"
    assert "drift" in decision.details


@pytest.mark.asyncio
async def test_pdp_trust_score_in_response(repo, contract_repo, trust_engine, registered_agent):
    """Successful ALLOW decisions include trust_score in the response details."""
    await contract_repo.create_contract(ContractCreate(
        id="c-trust-test",
        agent_id="test-agent-01",
        name="Researcher",
        allowed_tools=["web.search"],
        forbidden_tools=[],
        risk_level=RiskLevel.MEDIUM,
    ))

    fresh_tracker = ProvenanceTracker()
    set_provenance_tracker(fresh_tracker)

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=fresh_tracker,
    )
    set_pdp(pdp)

    request = ActionRequest(agent_id="test-agent-01", action="web.search")
    decision = await pdp.evaluate(request, agent=registered_agent)
    assert decision.decision == DecisionStatus.ALLOW
    assert "trust_score" in decision.details
    assert isinstance(decision.details["trust_score"], float)
