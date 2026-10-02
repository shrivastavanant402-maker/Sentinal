from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from agents.common.client import AegisMeshClient


class BaseAgent(ABC):
    """
    BaseAgent foundational class for autonomous agents interacting with AegisMesh.
    Encapsulates identity, state, and event dispatch.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client: Optional[AegisMeshClient] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.status = "active"
        self.client = client or AegisMeshClient()

    async def register(self) -> Dict[str, Any]:
        """
        Registers the agent's identity and capabilities with AegisMesh.
        """
        result = await self.client.register_agent(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            capabilities=self.capabilities,
            metadata=self.metadata
        )
        self.status = result.get("status", "active")
        return result

    async def emit_event(
        self,
        event_type: str,
        action: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Emits a structured runtime event to AegisMesh PEP / Event Ingestion.
        """
        return await self.client.emit_event(
            agent_id=self.agent_id,
            event_type=event_type,
            action=action,
            payload=payload,
            session_id=session_id
        )

    @abstractmethod
    async def run_step(self, session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Executes an agent step, generating appropriate events.
        """
        pass
