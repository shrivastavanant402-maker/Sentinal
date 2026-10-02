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
    Policy Decision Point (PEP/PDP) Engine.

    Synchronous evaluation pipeline:
      1. Identity Verification  — agent must be registered in the system
      2. Administrative Status  — quarantined / halted / paused checks
      3. Mission Contract       — looks up active contract for (agent_id, mission_id)
      4. Contract Validation    — validates allowed_tools / forbidden_tools allowlists
      5. Policy Evaluation      — synthesizes deterministic risk, status, and outcome
      6. Decision Dispatch      — constructs tamper-verifiable DecisionResponse

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
    ):
        self._contract_repo = contract_repository
        self._contract_validator = contract_validator or MissionContractValidator()
        self._policy_evaluator = policy_evaluator or RuntimePolicyEvaluator(
            contract_validator=self._contract_validator
        )
        self._identity_verifier = identity_verifier
        self._trust_evaluator = trust_evaluator
        self._provenance_evaluator = provenance_evaluator

    def _get_contract_repo(self) -> BaseContractRepository:
        if self._contract_repo is not None:
            return self._contract_repo
        return get_contract_repository()

    async def evaluate(
        self,
        request: ActionRequest,
        agent: Optional[AgentResponse] = None,
    ) -> DecisionResponse:
        """
        Evaluates an action request and returns a strongly-typed DecisionResponse.
        Never executes the action. Fails closed on any unexpected state.
        """
        # 1. Identity & Quarantine fast-path / initial policy evaluation
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

        # 2. Retrieve active Mission Contract for agent
        repo = self._get_contract_repo()
        contract: Optional[MissionContract] = await repo.get_contract_for_agent(
            agent_id=request.agent_id,
            mission_id=request.mission_id,
        )

        # 3. Validate against Mission Contract
        contract_result = self._contract_validator.validate(request, contract)

        # 4. Policy Engine Evaluation
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

        return DecisionResponse(
            decision=policy_result.status,
            allowed=policy_result.allowed,
            reason=policy_result.reason,
            risk_level=policy_result.risk_level,
            agent_id=request.agent_id,
            action=request.action,
            details=policy_result.details,
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
