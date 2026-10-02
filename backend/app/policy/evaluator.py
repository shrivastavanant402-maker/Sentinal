from dataclasses import dataclass
import logging
from typing import Any, Dict, Optional, Union

from backend.app.contracts.validator import (
    ContractOutcome,
    ContractValidationResult,
    MissionContractValidator,
)
from backend.app.policy.risk import classify_action_risk
from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.contract import MissionContract
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionReason,
    DecisionStatus,
    RiskLevel,
)

logger = logging.getLogger("aegismesh.policy.evaluator")


@dataclass
class PolicyEvaluationResult:
    allowed: bool
    status: DecisionStatus
    reason: Union[DecisionReason, str]
    risk_level: RiskLevel
    details: Dict[str, Any]


class RuntimePolicyEvaluator:
    """
    Deterministic runtime policy engine.
    Evaluates:
      - Agent identity & status
      - Tool risk classification
      - Active Mission Contract allowlists/denylists
    Enforces strict default-deny and fail-closed security.
    """

    def __init__(self, contract_validator: Optional[MissionContractValidator] = None):
        self.validator = contract_validator or MissionContractValidator()

    def evaluate(
        self,
        request: ActionRequest,
        agent: Optional[AgentResponse] = None,
        contract: Optional[MissionContract] = None,
        contract_result: Optional[ContractValidationResult] = None,
    ) -> PolicyEvaluationResult:
        """
        Evaluates an action request against agent state and mission contract.
        """
        risk = classify_action_risk(request.action)

        # ── 1. Identity Verification ─────────────────────────────────────────
        if agent is None:
            logger.warning(
                "Policy BLOCK: Unregistered agent '%s' requesting action '%s'",
                request.agent_id,
                request.action,
            )
            return PolicyEvaluationResult(
                allowed=False,
                status=DecisionStatus.BLOCK,
                reason=DecisionReason.INVALID_IDENTITY,
                risk_level=RiskLevel.HIGH,
                details={
                    "message": "Agent is not registered. Anonymous actions are strictly prohibited.",
                    "agent_id": request.agent_id,
                },
            )

        # ── 2. Quarantine Check ──────────────────────────────────────────────
        if agent.status == AgentStatus.QUARANTINED:
            logger.warning(
                "Policy QUARANTINE: Agent '%s' is quarantined, denying action '%s'",
                request.agent_id,
                request.action,
            )
            return PolicyEvaluationResult(
                allowed=False,
                status=DecisionStatus.QUARANTINE,
                reason=DecisionReason.AGENT_QUARANTINED,
                risk_level=RiskLevel.CRITICAL,
                details={
                    "message": "Agent is in quarantine. Execution suspended.",
                    "agent_status": agent.status.value,
                },
            )

        # ── 3. Administrative Operational State (Paused / Halted) ───────────
        if agent.status in (AgentStatus.HALTED, AgentStatus.PAUSED):
            logger.warning(
                "Policy BLOCK: Agent '%s' is in state %s, denying action '%s'",
                request.agent_id,
                agent.status.value,
                request.action,
            )
            return PolicyEvaluationResult(
                allowed=False,
                status=DecisionStatus.BLOCK,
                reason=DecisionReason.POLICY_VIOLATION,
                risk_level=RiskLevel.HIGH,
                details={
                    "message": f"Agent is {agent.status.value}. Actions prohibited.",
                    "agent_status": agent.status.value,
                },
            )

        # ── 4. Contract Evaluation ───────────────────────────────────────────
        if contract_result is None:
            contract_result = self.validator.validate(request, contract)

        if contract_result.outcome == ContractOutcome.NO_CONTRACT:
            logger.warning(
                "Policy BLOCK: No active mission contract for agent '%s' action '%s'",
                request.agent_id,
                request.action,
            )
            return PolicyEvaluationResult(
                allowed=False,
                status=DecisionStatus.BLOCK,
                reason=DecisionReason.CONTRACT_VIOLATION,
                risk_level=risk,
                details={
                    "message": "No active mission contract found. Default deny in effect.",
                    "action": request.action,
                },
            )

        if contract_result.outcome == ContractOutcome.DENY:
            reason = (
                DecisionReason.HIGH_RISK_ACTION
                if risk == RiskLevel.HIGH
                else DecisionReason.CONTRACT_VIOLATION
            )
            logger.warning(
                "Policy BLOCK: Contract '%s' denied action '%s' for agent '%s': %s",
                contract_result.contract_id,
                request.action,
                request.agent_id,
                contract_result.reason,
            )
            return PolicyEvaluationResult(
                allowed=False,
                status=DecisionStatus.BLOCK,
                reason=reason,
                risk_level=risk,
                details={
                    "message": contract_result.reason,
                    "contract_id": contract_result.contract_id,
                    "contract_details": contract_result.details or {},
                },
            )

        # ── 5. Explicit ALLOW ────────────────────────────────────────────────
        logger.info(
            "Policy ALLOW: Contract '%s' authorized action '%s' for agent '%s'",
            contract_result.contract_id,
            request.action,
            request.agent_id,
        )
        return PolicyEvaluationResult(
            allowed=True,
            status=DecisionStatus.ALLOW,
            reason=DecisionReason.ALLOWED_BY_POLICY,
            risk_level=risk,
            details={
                "message": contract_result.reason,
                "contract_id": contract_result.contract_id,
            },
        )
