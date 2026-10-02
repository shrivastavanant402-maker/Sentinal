from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Dict, Optional

from backend.app.schemas.contract import MissionContract
from backend.app.schemas.decision import ActionRequest

logger = logging.getLogger("aegismesh.contracts.validator")


class ContractOutcome(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    NO_CONTRACT = "NO_CONTRACT"


@dataclass
class ContractValidationResult:
    outcome: ContractOutcome
    reason: str
    contract_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class MissionContractValidator:
    """
    Evaluates action requests against an active MissionContract.
    Answers strictly whether the contract authorizes or prohibits the action.
    """

    def validate(
        self,
        request: ActionRequest,
        contract: Optional[MissionContract] = None,
    ) -> ContractValidationResult:
        """
        Validates an action against a mission contract.
        Returns domain-level ContractValidationResult.
        """
        # 1. No contract found
        if contract is None:
            return ContractValidationResult(
                outcome=ContractOutcome.NO_CONTRACT,
                reason="No active mission contract found for agent",
                contract_id=None,
                details={"agent_id": request.agent_id, "mission_id": request.mission_id},
            )

        # 2. Disabled contract
        if not contract.enabled:
            return ContractValidationResult(
                outcome=ContractOutcome.DENY,
                reason=f"Mission contract '{contract.id}' is disabled",
                contract_id=contract.id,
                details={"enabled": False},
            )

        # 3. Explicitly forbidden action
        if request.action in contract.forbidden_tools:
            return ContractValidationResult(
                outcome=ContractOutcome.DENY,
                reason=f"Action '{request.action}' is explicitly forbidden by contract '{contract.id}'",
                contract_id=contract.id,
                details={
                    "forbidden_tools": contract.forbidden_tools,
                    "action": request.action,
                },
            )

        # 4. Explicitly allowed action
        if contract.allowed_tools and request.action in contract.allowed_tools:
            return ContractValidationResult(
                outcome=ContractOutcome.ALLOW,
                reason=f"Action '{request.action}' is permitted by contract '{contract.id}'",
                contract_id=contract.id,
                details={
                    "allowed_tools": contract.allowed_tools,
                    "action": request.action,
                },
            )

        # 5. Action not in allowed tools list (Default Deny)
        return ContractValidationResult(
            outcome=ContractOutcome.DENY,
            reason=f"Action '{request.action}' is not in allowed_tools for contract '{contract.id}'",
            contract_id=contract.id,
            details={
                "allowed_tools": contract.allowed_tools,
                "action": request.action,
            },
        )
