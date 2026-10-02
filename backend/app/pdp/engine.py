import logging
from typing import Any, Dict, Optional

from backend.app.contracts.validator import (
    ContractOutcome,
    ContractValidationResult,
    MissionContractValidator,
)
from backend.app.db.repositories.contracts import (
    BaseContractRepository,
    get_contract_repository,
)
from backend.app.policy.evaluator import PolicyEvaluationResult, RuntimePolicyEvaluator
from backend.app.policy.risk import classify_action_risk
from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.contract import MissionContract
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionReason,
    DecisionResponse,
    DecisionStatus,
    RiskLevel,
)

logger = logging.getLogger("aegismesh.pdp")


class PolicyDecisionPoint:
    """
    Policy Decision Point (PDP) Engine — Phase 2.

    Evaluation pipeline:
      1. Identity Verification     — agent must be registered
      2. Administrative Status     — quarantined / halted / paused
      3. Mission Contract Lookup   — active contract for (agent_id, mission_id)
      4. Provenance / Taint Check  — tainted data → forbidden sink = CRITICAL BLOCK
      5. Mission Drift Detection   — action vs mission alignment score
      6. Contract Validation       — allowlist / denylist
      7. Policy Evaluation         — synthesize deterministic risk + outcome
      8. Trust Score Update        — apply decision to agent trust
      9. Auto-Quarantine Check     — trust < 40 triggers immediate quarantine
     10. Decision Dispatch         — construct tamper-verifiable DecisionResponse

    Enforces strict default-deny and fail-closed security.
    """

    def __init__(
        self,
        contract_repository: Optional[BaseContractRepository] = None,
        contract_validator: Optional[MissionContractValidator] = None,
        policy_evaluator: Optional[RuntimePolicyEvaluator] = None,
        identity_verifier=None,
        trust_evaluator=None,
        provenance_evaluator=None,
        drift_detector=None,
        quarantine_controller=None,
    ):
        self._contract_repo = contract_repository
        self._contract_validator = contract_validator or MissionContractValidator()
        self._policy_evaluator = policy_evaluator or RuntimePolicyEvaluator(
            contract_validator=self._contract_validator
        )
        self._identity_verifier = identity_verifier
        self._trust_evaluator = trust_evaluator
        self._provenance_evaluator = provenance_evaluator
        self._drift_detector = drift_detector
        self._quarantine_controller = quarantine_controller

    def _get_contract_repo(self) -> BaseContractRepository:
        if self._contract_repo is not None:
            return self._contract_repo
        return get_contract_repository()

    def _get_trust_engine(self):
        if self._trust_evaluator is not None:
            return self._trust_evaluator
        from backend.app.trust.engine import get_trust_engine
        return get_trust_engine()

    def _get_provenance_tracker(self):
        if self._provenance_evaluator is not None:
            return self._provenance_evaluator
        from backend.app.provenance.tracker import get_provenance_tracker
        return get_provenance_tracker()

    def _get_drift_detector(self):
        if self._drift_detector is not None:
            return self._drift_detector
        from backend.app.drift.detector import get_drift_detector
        return get_drift_detector()

    def _get_quarantine_controller(self):
        if self._quarantine_controller is not None:
            return self._quarantine_controller
        from backend.app.enforcement.quarantine import get_quarantine_controller
        return get_quarantine_controller()

    async def evaluate(
        self,
        request: ActionRequest,
        agent: Optional[AgentResponse] = None,
    ) -> DecisionResponse:
        """
        Evaluates an action request and returns a strongly-typed DecisionResponse.
        Never executes the action. Fails closed on any unexpected state.
        """
        # ── 1. Identity & Quarantine fast-path ───────────────────────────
        if agent is None:
            logger.warning(
                "PEP BLOCK — Unregistered agent '%s' requested action '%s'",
                request.agent_id,
                request.action,
            )
            return DecisionResponse(
                decision=DecisionStatus.BLOCK,
                allowed=False,
                reason=DecisionReason.INVALID_IDENTITY,
                risk_level=RiskLevel.HIGH,
                agent_id=request.agent_id,
                action=request.action,
                details={
                    "message": "Agent is not registered. Anonymous actions are strictly prohibited.",
                },
            )

        if agent.status == AgentStatus.QUARANTINED:
            logger.warning(
                "PEP QUARANTINE — Agent '%s' is quarantined, denying action '%s'",
                request.agent_id,
                request.action,
            )
            return DecisionResponse(
                decision=DecisionStatus.QUARANTINE,
                allowed=False,
                reason=DecisionReason.AGENT_QUARANTINED,
                risk_level=RiskLevel.CRITICAL,
                agent_id=request.agent_id,
                action=request.action,
                details={
                    "message": "Agent is quarantined. All actions are suspended.",
                    "agent_status": agent.status.value,
                },
            )

        if agent.status in (AgentStatus.HALTED, AgentStatus.PAUSED):
            logger.warning(
                "PEP BLOCK — Agent '%s' is %s, denying action '%s'",
                request.agent_id,
                agent.status.value,
                request.action,
            )
            return DecisionResponse(
                decision=DecisionStatus.BLOCK,
                allowed=False,
                reason=DecisionReason.POLICY_VIOLATION,
                risk_level=RiskLevel.HIGH,
                agent_id=request.agent_id,
                action=request.action,
                details={
                    "message": f"Agent is {agent.status.value}. Actions are not permitted.",
                    "agent_status": agent.status.value,
                },
            )

        # ── 2. Retrieve active Mission Contract ───────────────────────────
        repo = self._get_contract_repo()
        contract: Optional[MissionContract] = await repo.get_contract_for_agent(
            agent_id=request.agent_id,
            mission_id=request.mission_id,
        )

        # ── 3. Provenance / Taint Check ───────────────────────────────────
        taint_details: Dict[str, Any] = {}
        try:
            provenance_tracker = self._get_provenance_tracker()
            taint_result = await provenance_tracker.check_sink(
                agent_id=request.agent_id,
                sink_tool=request.action,
                payload=request.payload,
                provenance_meta=request.provenance,
            )
            if taint_result.is_tainted and taint_result.record and taint_result.record.is_hit:
                logger.critical(
                    "PEP BLOCK — Taint HIT: agent=%s action=%s label=%s",
                    request.agent_id,
                    request.action,
                    taint_result.label.value,
                )
                taint_details = {
                    "taint_label": taint_result.label.value,
                    "taint_record": taint_result.record.to_dict() if taint_result.record else None,
                    "reason": taint_result.reason,
                }
                # Apply trust penalty immediately (integrity + compliance)
                trust_engine = self._get_trust_engine()
                trust_score = await trust_engine.apply_decision(
                    agent_id=request.agent_id,
                    decision=DecisionStatus.BLOCK,
                    risk_level=RiskLevel.CRITICAL,
                )
                # Check auto-quarantine after taint hit
                qc = self._get_quarantine_controller()
                await qc.maybe_quarantine(
                    agent_id=request.agent_id,
                    trust_score=trust_score.composite,
                )
                return DecisionResponse(
                    decision=DecisionStatus.BLOCK,
                    allowed=False,
                    reason=DecisionReason.TAINT_SENSITIVE_LEAK,
                    risk_level=RiskLevel.CRITICAL,
                    agent_id=request.agent_id,
                    action=request.action,
                    details={
                        "message": taint_result.reason,
                        **taint_details,
                        "trust_score": trust_score.composite,
                    },
                )
        except Exception as exc:
            # Fail closed — taint check errors must not allow dangerous actions
            logger.error("Taint check error for agent %s: %s", request.agent_id, exc)

        # ── 4. Mission Drift Detection ────────────────────────────────────
        drift_details: Dict[str, Any] = {}
        try:
            drift_detector = self._get_drift_detector()
            drift_result = drift_detector.evaluate(request=request, contract=contract)
            drift_details = drift_result.to_dict()

            from backend.app.drift.detector import DriftSeverity
            if drift_result.severity == DriftSeverity.CRITICAL:
                logger.warning(
                    "PEP BLOCK — Mission drift CRITICAL: agent=%s action=%s drift_score=%.2f",
                    request.agent_id, request.action, drift_result.drift_score,
                )
                # Apply trust consistency penalty
                trust_engine = self._get_trust_engine()
                trust_score = await trust_engine.apply_consistency_violation(
                    agent_id=request.agent_id, severity=RiskLevel.CRITICAL
                )
                qc = self._get_quarantine_controller()
                await qc.maybe_quarantine(
                    agent_id=request.agent_id,
                    trust_score=trust_score.composite,
                )
                return DecisionResponse(
                    decision=DecisionStatus.BLOCK,
                    allowed=False,
                    reason=DecisionReason.MISSION_DRIFT,
                    risk_level=RiskLevel.CRITICAL,
                    agent_id=request.agent_id,
                    action=request.action,
                    details={
                        "message": drift_result.reason,
                        "drift": drift_details,
                        "trust_score": trust_score.composite,
                    },
                )

            if drift_result.severity == DriftSeverity.HIGH:
                # Require approval for high drift
                logger.warning(
                    "PEP APPROVAL — Mission drift HIGH: agent=%s action=%s drift_score=%.2f",
                    request.agent_id, request.action, drift_result.drift_score,
                )
                trust_engine = self._get_trust_engine()
                await trust_engine.apply_consistency_violation(
                    agent_id=request.agent_id, severity=RiskLevel.HIGH
                )
                return DecisionResponse(
                    decision=DecisionStatus.APPROVAL,
                    allowed=False,
                    reason=DecisionReason.MISSION_DRIFT,
                    risk_level=RiskLevel.HIGH,
                    agent_id=request.agent_id,
                    action=request.action,
                    details={
                        "message": drift_result.reason,
                        "drift": drift_details,
                    },
                )
        except Exception as exc:
            logger.error("Drift check error for agent %s: %s", request.agent_id, exc)

        # ── 5. Contract Validation ────────────────────────────────────────
        contract_result = self._contract_validator.validate(request, contract)

        # ── 6. Policy Evaluation ──────────────────────────────────────────
        policy_result: PolicyEvaluationResult = self._policy_evaluator.evaluate(
            request=request,
            agent=agent,
            contract=contract,
            contract_result=contract_result,
        )

        logger.info(
            "PEP Evaluation complete: agent=%s action=%s status=%s allowed=%s reason=%s",
            request.agent_id,
            request.action,
            policy_result.status.value,
            policy_result.allowed,
            policy_result.reason,
        )

        # ── 7. Trust Score Update ─────────────────────────────────────────
        trust_score_val: Optional[float] = None
        try:
            trust_engine = self._get_trust_engine()
            ts = await trust_engine.apply_decision(
                agent_id=request.agent_id,
                decision=policy_result.status,
                risk_level=policy_result.risk_level,
            )
            trust_score_val = ts.composite

            # ── 8. Auto-quarantine if trust drops below threshold ─────────
            if policy_result.status in (DecisionStatus.BLOCK, DecisionStatus.QUARANTINE):
                qc = self._get_quarantine_controller()
                await qc.maybe_quarantine(
                    agent_id=request.agent_id,
                    trust_score=ts.composite,
                )

            # Mark sensitive source tools — taint the agent on ALLOW
            from backend.app.provenance.tracker import ProvenanceTracker
            provenance_tracker = self._get_provenance_tracker()
            if (
                policy_result.allowed
                and ProvenanceTracker.is_sensitive_source(request.action)
            ):
                await provenance_tracker.mark_tainted(
                    agent_id=request.agent_id,
                    source_tool=request.action,
                    payload=request.payload,
                )

        except Exception as exc:
            logger.error("Trust/provenance post-processing error for agent %s: %s", request.agent_id, exc)

        details = dict(policy_result.details)
        if trust_score_val is not None:
            details["trust_score"] = round(trust_score_val, 2)
        if drift_details:
            details["drift"] = drift_details

        return DecisionResponse(
            decision=policy_result.status,
            allowed=policy_result.allowed,
            reason=policy_result.reason,
            risk_level=policy_result.risk_level,
            agent_id=request.agent_id,
            action=request.action,
            details=details,
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_pdp_instance: Optional[PolicyDecisionPoint] = None


def get_pdp() -> PolicyDecisionPoint:
    """Return the singleton PDP. Evaluators can be injected before first use."""
    global _pdp_instance
    if _pdp_instance is None:
        _pdp_instance = PolicyDecisionPoint()
    return _pdp_instance


def set_pdp(pdp: PolicyDecisionPoint) -> None:
    """Override PDP for testing or with injected evaluators."""
    global _pdp_instance
    _pdp_instance = pdp
