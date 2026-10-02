import pytest
from pydantic import ValidationError
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionResponse,
    DecisionStatus,
    DecisionReason,
    RiskLevel
)
from backend.app.security.exceptions import (
    SecurityError,
    ActionDenied,
    AgentQuarantined,
    ApprovalRequired,
    InvalidAgentIdentity
)


def test_action_request_valid():
    req = ActionRequest(
        agent_id="researcher-01",
        action="web.search",
        payload={"query": "Zero day vulnerabilities"},
        mission_id="mission-alpha",
        session_id="session-42",
        provenance={"taint": ["untrusted_web"]}
    )
    assert req.agent_id == "researcher-01"
    assert req.action == "web.search"
    assert req.payload["query"] == "Zero day vulnerabilities"
    assert req.mission_id == "mission-alpha"
    assert req.session_id == "session-42"
    assert req.provenance == {"taint": ["untrusted_web"]}


def test_action_request_minimal():
    req = ActionRequest(
        agent_id="executor-01",
        action="report.generate"
    )
    assert req.agent_id == "executor-01"
    assert req.action == "report.generate"
    assert req.payload == {}
    assert req.mission_id is None
    assert req.session_id is None
    assert req.provenance is None


def test_action_request_missing_required():
    with pytest.raises(ValidationError):
        ActionRequest(agent_id="planner-01")  # missing action


@pytest.mark.parametrize("status,allowed", [
    (DecisionStatus.ALLOW, True),
    (DecisionStatus.BLOCK, False),
    (DecisionStatus.APPROVAL, False),
    (DecisionStatus.QUARANTINE, False),
])
def test_all_four_decision_states(status, allowed):
    resp = DecisionResponse(
        decision=status,
        allowed=allowed,
        reason=DecisionReason.ALLOWED_BY_POLICY if allowed else DecisionReason.POLICY_VIOLATION,
        risk_level=RiskLevel.LOW if allowed else RiskLevel.HIGH,
        agent_id="researcher-01",
        action="web.search",
        event_id="ev-001",
        details={"evaluated_rules": ["rule_allow_search"]}
    )
    assert resp.decision == status
    assert resp.allowed == allowed
    assert resp.agent_id == "researcher-01"
    assert resp.action == "web.search"


def test_invalid_decision_status():
    with pytest.raises(ValidationError):
        DecisionResponse(
            decision="INVALID_STATUS",  # Not in ALLOW, BLOCK, APPROVAL, QUARANTINE
            allowed=True,
            agent_id="researcher-01",
            action="web.search"
        )


def test_security_exceptions_hierarchy():
    err = ActionDenied("Blocked by contract", details={"rule": "deny_export"})
    assert isinstance(err, SecurityError)
    assert str(err) == "Blocked by contract"
    assert err.details == {"rule": "deny_export"}

    assert issubclass(AgentQuarantined, SecurityError)
    assert issubclass(ApprovalRequired, SecurityError)
    assert issubclass(InvalidAgentIdentity, SecurityError)
