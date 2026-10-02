import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.agent import AgentStatus
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionResponse,
    DecisionReason,
    DecisionStatus,
    RiskLevel,
)

logger = logging.getLogger("aegismesh.pdp")


# ---------------------------------------------------------------------------
# Risk classification — deterministic, no fake policy engine
# ---------------------------------------------------------------------------

# Actions that are considered high-risk regardless of agent/contract status.
# Kept minimal and explicit.
HIGH_RISK_ACTIONS: frozenset = frozenset({
    "database.export",
    "shell.exec",
    "external.post",
    "fs.write",
    "secret.read",
})


def _classify_risk(action: str) -> RiskLevel:
    """Deterministic risk classification based on tool name."""
    if action in HIGH_RISK_ACTIONS:
        return RiskLevel.HIGH
    if action.startswith("database.") or action.startswith("secret."):
        return RiskLevel.HIGH
    if action.startswith("external.") or action.startswith("shell."):
        return RiskLevel.HIGH
    if action.startswith("fs."):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ---------------------------------------------------------------------------
# PDP Engine
# ---------------------------------------------------------------------------


class PolicyDecisionPoint:
    """
    Minimal, deterministic Policy Decision Point.

    Evaluation pipeline (each stage can short-circuit):
      1. Identity presence  — agent must be registered
      2. Quarantine status  — quarantined agent → QUARANTINE
      3. Risk classification — high-risk action → BLOCK (until contract permits it)
      4. Default: ALLOW for known, active, low/medium risk actions

    Evaluators (identity, contract, policy, trust, provenance) are injected via
    the ``evaluators`` dict so future implementations drop in without touching
    this class. For now all are None / not invoked.
    """

    def __init__(
        self,
        identity_verifier=None,
        contract_evaluator=None,
        policy_evaluator=None,
        trust_evaluator=None,
        provenance_evaluator=None,
    ):
        self._identity_verifier = identity_verifier
        self._contract_evaluator = contract_evaluator
        self._policy_evaluator = policy_evaluator
        self._trust_evaluator = trust_evaluator
        self._provenance_evaluator = provenance_evaluator

    async def evaluate(
        self,
        request: ActionRequest,
        agent: Optional[Any] = None,  # AgentResponse or None
    ) -> DecisionResponse:
        """
        Evaluate an action request and return a DecisionResponse.
        ``agent`` is the database record for ``request.agent_id``.
        Pass None when the agent is not registered.
        """
        risk = _classify_risk(request.action)

        # ── STAGE 1: Identity / registration check ──────────────────────────
        if agent is None:
            logger.warning(
                "PEP BLOCK — unregistered agent '%s' requested '%s'",
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
                    "message": "Agent is not registered. Registration required before action can be authorised.",
                },
            )

        # ── STAGE 2: Quarantine check ────────────────────────────────────────
        if agent.status == AgentStatus.QUARANTINED:
            logger.warning(
                "PEP QUARANTINE — agent '%s' is quarantined, blocked '%s'",
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

        # ── STAGE 3: Halted / paused check ──────────────────────────────────
        if agent.status in (AgentStatus.HALTED, AgentStatus.PAUSED):
            logger.warning(
                "PEP BLOCK — agent '%s' is %s, blocked '%s'",
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

        # ── STAGE 4: High-risk action gate ──────────────────────────────────
        # Until mission contracts and policy engine are implemented, high-risk
        # actions are blocked unconditionally (safe default).
        if risk == RiskLevel.HIGH:
            logger.warning(
                "PEP BLOCK — high-risk action '%s' by agent '%s' (no contract approved)",
                request.action,
                request.agent_id,
            )
            return DecisionResponse(
                decision=DecisionStatus.BLOCK,
                allowed=False,
                reason=DecisionReason.HIGH_RISK_ACTION,
                risk_level=risk,
                agent_id=request.agent_id,
                action=request.action,
                details={
                    "message": (
                        "High-risk action requires an approved mission contract. "
                        "Contract evaluation not yet configured."
                    ),
                    "action": request.action,
                },
            )

        # ── STAGE 5: Future evaluators (no-op until implemented) ────────────
        # When injected evaluators are non-None they will be called here.
        # They return a partial result dict; any 'allowed=False' short-circuits.
        for evaluator_name, evaluator in [
            ("policy", self._policy_evaluator),
            ("trust", self._trust_evaluator),
            ("provenance", self._provenance_evaluator),
            ("contract", self._contract_evaluator),
        ]:
            if evaluator is not None:
                result = await evaluator.evaluate_policy(request)  # type: ignore[union-attr]
                if not result.get("allowed", True):
                    logger.warning(
                        "PEP BLOCK — %s evaluator blocked '%s' by agent '%s': %s",
                        evaluator_name,
                        request.action,
                        request.agent_id,
                        result.get("reason"),
                    )
                    return DecisionResponse(
                        decision=DecisionStatus.BLOCK,
                        allowed=False,
                        reason=result.get("reason", DecisionReason.POLICY_VIOLATION),
                        risk_level=risk,
                        agent_id=request.agent_id,
                        action=request.action,
                        details=result,
                    )

        # ── DEFAULT: ALLOW ───────────────────────────────────────────────────
        logger.info(
            "PEP ALLOW — agent '%s' action '%s' (risk: %s)",
            request.agent_id,
            request.action,
            risk.value,
        )
        return DecisionResponse(
            decision=DecisionStatus.ALLOW,
            allowed=True,
            reason=DecisionReason.ALLOWED_BY_POLICY,
            risk_level=risk,
            agent_id=request.agent_id,
            action=request.action,
            details={"message": "Action permitted by current policy configuration."},
        )


# ---------------------------------------------------------------------------
# Singleton accessor (parallel to get_repository())
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
