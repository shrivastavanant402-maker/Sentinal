from typing import Any, Dict, List, Optional
from agents.common.base import BaseAgent
from agents.common.client import AegisMeshClient


class ResearcherAgent(BaseAgent):
    """
    Researcher agent responsible for web search and research database access.
    Protected tool actions are guarded by PEP before execution.
    """

    def __init__(
        self,
        agent_id: str = "researcher-01",
        name: str = "Deep Researcher",
        client: Optional[AegisMeshClient] = None,
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="researcher",
            capabilities=["web.search", "web.read", "research_db.read"],
            metadata={"priority": "medium", "domain": "intelligence"},
            client=client,
        )

    # -----------------------------------------------------------------------
    # Tool Execution Implementations (Actual Tools)
    # -----------------------------------------------------------------------

    def _exec_web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Underlying tool execution for web search."""
        return {
            "query": query,
            "results_count": max_results,
            "status": "success",
            "results": [
                {
                    "title": f"AegisMesh Intelligence on: {query}",
                    "url": f"https://intel.aegismesh.internal/search?q={query}",
                    "summary": f"Runtime verification evidence gathered for '{query}'.",
                }
            ],
        }

    def _exec_database_export(self, table: str) -> Dict[str, Any]:
        """Underlying tool execution for database export (high-risk)."""
        return {
            "table": table,
            "exported_rows": 100,
            "format": "json",
            "status": "exported",
        }

    # -----------------------------------------------------------------------
    # Protected Tool Methods (Guarded by PEP)
    # -----------------------------------------------------------------------

    async def execute_web_search(
        self,
        query: str,
        max_results: int = 5,
        session_id: Optional[str] = "session-001",
    ) -> Dict[str, Any]:
        """
        Executes web.search protected by PEP guard.
        ALLOW -> executes tool and returns results.
        BLOCK/DENY -> raises SecurityError; tool never runs.
        """
        payload = {"query": query, "max_results": max_results}
        decision = await self.guard(
            action="web.search",
            payload=payload,
            session_id=session_id,
        )
        return self._exec_web_search(query=query, max_results=max_results)

    async def execute_database_export(
        self,
        table: str,
        session_id: Optional[str] = "session-001",
    ) -> Dict[str, Any]:
        """
        Attempts database.export protected by PEP guard.
        Should be BLOCKED because database.export is classified as high-risk.
        """
        payload = {"table": table}
        decision = await self.guard(
            action="database.export",
            payload=payload,
            session_id=session_id,
        )
        return self._exec_database_export(table=table)

    # -----------------------------------------------------------------------
    # Event Emission / Foundation Workflow
    # -----------------------------------------------------------------------

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        session_id: Optional[str] = "session-001",
    ) -> Dict[str, Any]:
        """
        Emits tool_call_request for web.search to AegisMesh event ledger.
        """
        payload = {
            "tool": "web.search",
            "query": query,
            "max_results": max_results,
            "agent": self.agent_id,
        }
        return await self.emit_event(
            event_type="tool_call_request",
            action="web.search",
            payload=payload,
            session_id=session_id,
        )

    async def run_step(self, session_id: Optional[str] = "session-001", **kwargs) -> Dict[str, Any]:
        """
        Generates standard test web search event.
        """
        query = kwargs.get("query", "Autonomous agent runtime integrity systems security trends 2026")
        max_results = kwargs.get("max_results", 5)
        return await self.search_web(query=query, max_results=max_results, session_id=session_id)
