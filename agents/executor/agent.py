from typing import Any, Dict, Optional
from agents.common.base import BaseAgent
from agents.common.client import AegisMeshClient


class ExecutorAgent(BaseAgent):
    """
    Executor agent responsible for artifact compilation and action execution.
    Emits tool_call_request -> report.generate.
    """

    def __init__(
        self,
        agent_id: str = "executor-01",
        name: str = "Task Executor",
        client: Optional[AegisMeshClient] = None
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="executor",
            capabilities=["report.generate", "fs.read", "fs.write"],
            metadata={"priority": "high", "domain": "execution"},
            client=client
        )

    async def generate_report(
        self,
        title: str,
        template: str = "executive_briefing",
        session_id: Optional[str] = "session-001"
    ) -> Dict[str, Any]:
        """
        Emits tool_call_request for report.generate to AegisMesh.
        """
        payload = {
            "tool": "report.generate",
            "title": title,
            "template": template,
            "agent": self.agent_id,
            "output_format": "markdown"
        }
        return await self.emit_event(
            event_type="tool_call_request",
            action="report.generate",
            payload=payload,
            session_id=session_id
        )

    async def run_step(self, session_id: Optional[str] = "session-001", **kwargs) -> Dict[str, Any]:
        """
        Generates standard test report compilation event.
        """
        title = kwargs.get("title", "AegisMesh Autonomous Integrity Assessment")
        template = kwargs.get("template", "executive_briefing")
        return await self.generate_report(title=title, template=template, session_id=session_id)
