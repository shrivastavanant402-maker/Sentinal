from typing import Any, Dict, Optional
from agents.common.base import BaseAgent
from agents.common.client import AegisMeshClient


class PlannerAgent(BaseAgent):
    """
    Planner agent responsible for goal decomposition and plan declaration.
    Cannot directly execute high-risk or external tools.
    """

    def __init__(
        self,
        agent_id: str = "planner-01",
        name: str = "Lead Planner",
        client: Optional[AegisMeshClient] = None
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            role="planner",
            capabilities=["plan.declare", "task.delegate", "objective.decompose"],
            metadata={"priority": "high", "domain": "orchestration"},
            client=client
        )

    async def declare_plan(
        self,
        goal: str,
        steps: list[dict],
        session_id: Optional[str] = "session-001"
    ) -> Dict[str, Any]:
        """
        Emits plan_declared event to AegisMesh.
        """
        payload = {
            "goal": goal,
            "total_steps": len(steps),
            "steps": steps,
            "planner_agent": self.agent_id
        }
        return await self.emit_event(
            event_type="plan_declared",
            action="plan.declare",
            payload=payload,
            session_id=session_id
        )

    async def run_step(self, session_id: Optional[str] = "session-001", **kwargs) -> Dict[str, Any]:
        """
        Generates standard test plan declaration event.
        """
        goal = kwargs.get("goal", "Analyze security posture and produce verified report")
        steps = kwargs.get("steps", [
            {"step_id": 1, "agent": "researcher-01", "task": "Search for CVE vulnerabilities"},
            {"step_id": 2, "agent": "executor-01", "task": "Compile executive risk report"}
        ])
        return await self.declare_plan(goal=goal, steps=steps, session_id=session_id)
