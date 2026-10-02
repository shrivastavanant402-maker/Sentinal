from abc import ABC, abstractmethod
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional
import httpx

from agents.common.client import AegisMeshClient
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionReason,
    DecisionResponse,
    DecisionStatus,
)
from backend.app.security.exceptions import (
    ActionDenied,
    AgentQuarantined,
    ApprovalRequired,
    InvalidAgentIdentity,
    SecurityError,
)

logger = logging.getLogger("aegismesh.agent")


class BaseAgent(ABC):
    """
    BaseAgent foundational class for autonomous agents interacting with AegisMesh.
    Encapsulates identity, state, PEP security guard, and event dispatch.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client: Optional[AegisMeshClient] = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.status = "active"
        self.client = client or AegisMeshClient()
        self.last_decision: Optional[DecisionResponse] = None

    async def register(self) -> Dict[str, Any]:
        """
        Registers the agent's identity and capabilities with AegisMesh.
        """
        result = await self.client.register_agent(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            capabilities=self.capabilities,
            metadata=self.metadata,
        )
        self.status = result.get("status", "active")
        return result

    async def guard(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> DecisionResponse:
        """
        Synchronous Policy Enforcement Point (PEP) security gate.
        MUST be called before executing any protected action.

        Fail-Closed Contract:
        - ALLOW (allowed=True)  -> returns DecisionResponse
        - BLOCK                 -> raises ActionDenied (or InvalidAgentIdentity)
        - QUARANTINE            -> raises AgentQuarantined
        - APPROVAL              -> raises ApprovalRequired
        - PEP unreachable/error -> raises ActionDenied (FAIL CLOSED)
        - Malformed response    -> raises ActionDenied (FAIL CLOSED)
        """
        request = ActionRequest(
            agent_id=self.agent_id,
            action=action,
            payload=payload or {},
            session_id=session_id,
            mission_id=mission_id,
            provenance=provenance,
        )

        try:
            raw_response = await self.client.enforce(request)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "PEP enforcement returned HTTP %s for agent %s action %s",
                exc.response.status_code,
                self.agent_id,
                action,
            )
            raise ActionDenied(
                f"PEP enforcement failed with HTTP {exc.response.status_code}",
                details={"status_code": exc.response.status_code, "action": action},
            ) from exc
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.error(
                "PEP communication error (fail-closed) for agent %s action %s: %s",
                self.agent_id,
                action,
                exc,
            )
            raise ActionDenied(
                f"PEP communication failure (fail-closed): {exc}",
                details={"error": str(exc), "action": action},
            ) from exc
        except SecurityError:
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error contacting PEP for agent %s action %s: %s",
                self.agent_id,
                action,
                exc,
            )
            raise ActionDenied(
                f"PEP unexpected error (fail-closed): {exc}",
                details={"error": str(exc), "action": action},
            ) from exc

        # Parse into typed DecisionResponse model
        try:
            decision = DecisionResponse(**raw_response)
            self.last_decision = decision
        except Exception as exc:
            logger.error("PEP returned malformed decision response: %s", exc)
            raise ActionDenied(
                f"PEP returned malformed decision response: {exc}",
                details={"raw_response": raw_response, "error": str(exc)},
            ) from exc

        # Enforce outcome according to DecisionStatus
        if decision.decision == DecisionStatus.ALLOW and decision.allowed:
            return decision

        reason_val = (
            decision.reason.value
            if hasattr(decision.reason, "value")
            else str(decision.reason)
        )

        if decision.decision == DecisionStatus.BLOCK:
            if (
                decision.reason == DecisionReason.INVALID_IDENTITY
                or reason_val == "INVALID_IDENTITY"
            ):
                raise InvalidAgentIdentity(
                    f"Action '{action}' blocked: invalid agent identity",
                    details=decision.details,
                )
            raise ActionDenied(
                f"Action '{action}' blocked: {reason_val}",
                details=decision.details,
            )

        if decision.decision == DecisionStatus.QUARANTINE:
            raise AgentQuarantined(
                f"Agent '{self.agent_id}' is quarantined. Action '{action}' denied.",
                details=decision.details,
            )

        if decision.decision == DecisionStatus.APPROVAL:
            raise ApprovalRequired(
                f"Action '{action}' requires authorization approval.",
                details=decision.details,
            )

        # Catch-all fail closed for any unexpected decision state
        raise ActionDenied(
            f"Action '{action}' denied: unexpected decision status '{decision.decision}'",
            details=decision.details,
        )

    async def execute_protected(
        self,
        action: str,
        payload: Dict[str, Any],
        executor: Callable[..., Any],
        *args,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Enforces that `executor` runs ONLY after the PEP grants ALLOW.
        If blocked, quarantined, approval-required, or error occurs,
        a SecurityError is raised and `executor` is NEVER invoked.
        """
        decision = await self.guard(
            action=action,
            payload=payload,
            session_id=session_id,
            mission_id=mission_id,
            provenance=provenance,
        )

        if not decision.allowed:
            raise ActionDenied(
                f"Action '{action}' was not allowed: {decision.reason}",
                details=decision.details,
            )

        if inspect.iscoroutinefunction(executor):
            return await executor(*args, **kwargs)
        return executor(*args, **kwargs)

    async def emit_event(
        self,
        event_type: str,
        action: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Emits a structured runtime event to AegisMesh Event Ingestion.
        """
        return await self.client.emit_event(
            agent_id=self.agent_id,
            event_type=event_type,
            action=action,
            payload=payload,
            session_id=session_id,
        )

    @abstractmethod
    async def run_step(self, session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Executes an agent step, generating appropriate events.
        """
        pass
