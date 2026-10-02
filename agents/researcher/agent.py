from typing import Any, Dict, Optional
from agents.common.base import BaseAgent
from agents.common.client import AegisMeshClient


class ResearcherAgent(BaseAgent):
    """
    Researcher agent responsible for web search and research database access.
    Emits tool_call_request -> web.search.
    """

    def __init__(
        self,
        agent_id: str = "researcher-01",
        name: str = "Deep Researcher",
        client: Optional[AegisMeshClient] = None
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="researcher",
            capabilities=["web.search", "web.read", "research_db.read"],
            metadata={"priority": "medium", "domain": "intelligence"},
            client=client
        )

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        session_id: Optional[str] = "session-001"
    ) -> Dict[str, Any]:
        """
        Emits tool_call_request for web.search to AegisMesh.
        """
        payload = {
            "tool": "web.search",
            "query": query,
            "max_results": max_results,
            "agent": self.agent_id
        }
        return await self.emit_event(
            event_type="tool_call_request",
            action="web.search",
            payload=payload,
            session_id=session_id
        )

    async def run_step(self, session_id: Optional[str] = "session-001", **kwargs) -> Dict[str, Any]:
        """
        Generates standard test web search event.
        """
        query = kwargs.get("query", "Autonomous agent runtime integrity systems security trends 2026")
        max_results = kwargs.get("max_results", 5)
        return await self.search_web(query=query, max_results=max_results, session_id=session_id)
