from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from agents.common.client import AegisMeshClient
from agents.planner.agent import PlannerAgent
from agents.researcher.agent import ResearcherAgent
from agents.executor.agent import ExecutorAgent
from backend.app.schemas.decision import DecisionStatus
from backend.app.security.exceptions import (
    ActionDenied,
    AgentQuarantined,
    ApprovalRequired,
    InvalidAgentIdentity,
    SecurityError,
)

logger = logging.getLogger("aegismesh.orchestrator")


class MissionResult(BaseModel):
    """
    Structured outcome of a multi-agent mission orchestrated under
    AegisMesh runtime integrity enforcement.
    """
    mission_id: str = Field(..., description="Unique mission correlation identifier")
    session_id: str = Field(..., description="Session context identifier")
    goal: str = Field(..., description="High-level objective provided to the mission")
    status: str = Field(..., description="Execution status: COMPLETED, BLOCKED, QUARANTINED, FAILED")
    planner_result: Optional[Dict[str, Any]] = Field(None, description="Output from PlannerAgent")
    researcher_result: Optional[Dict[str, Any]] = Field(None, description="Output from ResearcherAgent")
    executor_result: Optional[Dict[str, Any]] = Field(None, description="Output from ExecutorAgent")
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered execution step audit records")
    event_ids: List[str] = Field(default_factory=list, description="Captured cryptographic ledger event IDs")
    error: Optional[str] = Field(None, description="Error message if execution did not complete")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Structured error/policy decision details")


class MissionCoordinator:
    """
    Coordinates multi-agent missions across:
        Planner -> Researcher -> Executor
    while preserving strict AegisMesh PEP enforcement boundaries for every action.
    """

    def __init__(
        self,
        planner: Optional[PlannerAgent] = None,
        researcher: Optional[ResearcherAgent] = None,
        executor: Optional[ExecutorAgent] = None,
        client: Optional[AegisMeshClient] = None,
    ):
        self.client = client or AegisMeshClient()
        self.planner = planner or PlannerAgent(client=self.client)
        self.researcher = researcher or ResearcherAgent(client=self.client)
        self.executor = executor or ExecutorAgent(client=self.client)

    async def run_mission(
        self,
        goal: str,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        raise_on_failure: bool = False,
    ) -> MissionResult:
        """
        Executes a multi-agent mission in fail-closed sequence:
            1. PlannerAgent.execute_delegate_task() -> task.delegate (PEP guard)
            2. ResearcherAgent.execute_web_search() -> web.search (PEP guard)
            3. ExecutorAgent.execute_generate_report() -> report.generate (PEP guard)

        If any agent action is blocked, quarantined, or fails, the mission halts
        immediately and downstream agents are NEVER executed.
        """
        mid = mission_id or f"mission-{uuid.uuid4().hex[:8]}"
        sid = session_id or f"session-{uuid.uuid4().hex[:8]}"
        trace: List[Dict[str, Any]] = []
        event_ids: List[str] = []

        planner_out: Optional[Dict[str, Any]] = None
        researcher_out: Optional[Dict[str, Any]] = None
        executor_out: Optional[Dict[str, Any]] = None

        logger.info("Starting mission [%s] session [%s] with goal: %s", mid, sid, goal)

        # -------------------------------------------------------------------
        # STEP 1: PlannerAgent
        # -------------------------------------------------------------------
        try:
            planner_out = await self.planner.execute_delegate_task(
                target_agent=self.researcher.agent_id,
                task=f"Research intelligence for: {goal}",
                session_id=sid,
                mission_id=mid,
            )
            event_id = getattr(self.planner.last_decision, "event_id", None)
            if event_id and event_id not in event_ids:
                event_ids.append(event_id)

            trace.append({
                "step": 1,
                "agent_id": self.planner.agent_id,
                "action": "task.delegate",
                "status": "ALLOW",
                "decision": "ALLOW",
                "event_id": event_id,
                "reason": str(getattr(self.planner.last_decision, "reason", "ALLOWED_BY_POLICY")),
                "output": planner_out,
            })
            logger.info("Step 1 (Planner) completed successfully under PEP ALLOW. Event: %s", event_id)
        except SecurityError as exc:
            event_id = getattr(self.planner.last_decision, "event_id", None)
            if event_id and event_id not in event_ids:
                event_ids.append(event_id)
            status = "QUARANTINED" if isinstance(exc, AgentQuarantined) else "BLOCKED"
            trace.append({
                "step": 1,
                "agent_id": self.planner.agent_id,
                "action": "task.delegate",
                "status": status,
                "decision": status,
                "event_id": event_id,
                "error": str(exc),
                "details": getattr(exc, "details", {}),
            })
            logger.warning("Step 1 (Planner) rejected by PEP [%s]: %s", status, exc)
            if raise_on_failure:
                raise
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status=status,
                planner_result=None,
                researcher_result=None,
                executor_result=None,
                execution_trace=trace,
                event_ids=event_ids,
                error=str(exc),
                error_details=getattr(exc, "details", {}),
            )
        except Exception as exc:
            trace.append({
                "step": 1,
                "agent_id": self.planner.agent_id,
                "action": "task.delegate",
                "status": "FAILED",
                "error": str(exc),
            })
            logger.error("Step 1 (Planner) encountered unexpected failure: %s", exc)
            if raise_on_failure:
                raise
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status="FAILED",
                planner_result=None,
                researcher_result=None,
                executor_result=None,
                execution_trace=trace,
                event_ids=event_ids,
                error=str(exc),
            )

        # -------------------------------------------------------------------
        # STEP 2: ResearcherAgent
        # -------------------------------------------------------------------
        try:
            # Context passed forward from planner
            research_query = planner_out.get("task", goal)
            researcher_out = await self.researcher.execute_web_search(
                query=research_query,
                max_results=3,
                session_id=sid,
                mission_id=mid,
            )
            event_id = getattr(self.researcher.last_decision, "event_id", None)
            if event_id and event_id not in event_ids:
                event_ids.append(event_id)

            trace.append({
                "step": 2,
                "agent_id": self.researcher.agent_id,
                "action": "web.search",
                "status": "ALLOW",
                "decision": "ALLOW",
                "event_id": event_id,
                "reason": str(getattr(self.researcher.last_decision, "reason", "ALLOWED_BY_POLICY")),
                "output": researcher_out,
            })
            logger.info("Step 2 (Researcher) completed successfully under PEP ALLOW. Event: %s", event_id)
        except SecurityError as exc:
            event_id = getattr(self.researcher.last_decision, "event_id", None)
            if event_id and event_id not in event_ids:
                event_ids.append(event_id)
            status = "QUARANTINED" if isinstance(exc, AgentQuarantined) else "BLOCKED"
            trace.append({
                "step": 2,
                "agent_id": self.researcher.agent_id,
                "action": "web.search",
                "status": status,
                "decision": status,
                "event_id": event_id,
                "error": str(exc),
                "details": getattr(exc, "details", {}),
            })
            logger.warning("Step 2 (Researcher) rejected by PEP [%s]: %s", status, exc)
            if raise_on_failure:
                raise
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status=status,
                planner_result=planner_out,
                researcher_result=None,
                executor_result=None,
                execution_trace=trace,
                event_ids=event_ids,
                error=str(exc),
                error_details=getattr(exc, "details", {}),
            )
        except Exception as exc:
            trace.append({
                "step": 2,
                "agent_id": self.researcher.agent_id,
                "action": "web.search",
                "status": "FAILED",
                "error": str(exc),
            })
            logger.error("Step 2 (Researcher) encountered unexpected failure: %s", exc)
            if raise_on_failure:
                raise
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status="FAILED",
                planner_result=planner_out,
                researcher_result=None,
                executor_result=None,
                execution_trace=trace,
                event_ids=event_ids,
                error=str(exc),
            )

        # -------------------------------------------------------------------
        # STEP 3: ExecutorAgent
        # -------------------------------------------------------------------
        try:
            # Context passed forward from research / mission
            report_title = f"Executive Intelligence Report: {goal}"
            executor_out = await self.executor.execute_generate_report(
                title=report_title,
                template="executive_briefing",
                session_id=sid,
                mission_id=mid,
            )
            event_id = getattr(self.executor.last_decision, "event_id", None)
            if event_id and event_id not in event_ids:
                event_ids.append(event_id)

            trace.append({
                "step": 3,
                "agent_id": self.executor.agent_id,
                "action": "report.generate",
                "status": "ALLOW",
                "decision": "ALLOW",
                "event_id": event_id,
                "reason": str(getattr(self.executor.last_decision, "reason", "ALLOWED_BY_POLICY")),
                "output": executor_out,
            })
            logger.info("Step 3 (Executor) completed successfully under PEP ALLOW. Event: %s", event_id)
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status="COMPLETED",
                planner_result=planner_out,
                researcher_result=researcher_out,
                executor_result=executor_out,
                execution_trace=trace,
                event_ids=event_ids,
            )
        except SecurityError as exc:
            event_id = getattr(self.executor.last_decision, "event_id", None)
            if event_id and event_id not in event_ids:
                event_ids.append(event_id)
            status = "QUARANTINED" if isinstance(exc, AgentQuarantined) else "BLOCKED"
            trace.append({
                "step": 3,
                "agent_id": self.executor.agent_id,
                "action": "report.generate",
                "status": status,
                "decision": status,
                "event_id": event_id,
                "error": str(exc),
                "details": getattr(exc, "details", {}),
            })
            logger.warning("Step 3 (Executor) rejected by PEP [%s]: %s", status, exc)
            if raise_on_failure:
                raise
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status=status,
                planner_result=planner_out,
                researcher_result=researcher_out,
                executor_result=None,
                execution_trace=trace,
                event_ids=event_ids,
                error=str(exc),
                error_details=getattr(exc, "details", {}),
            )
        except Exception as exc:
            trace.append({
                "step": 3,
                "agent_id": self.executor.agent_id,
                "action": "report.generate",
                "status": "FAILED",
                "error": str(exc),
            })
            logger.error("Step 3 (Executor) encountered unexpected failure: %s", exc)
            if raise_on_failure:
                raise
            return MissionResult(
                mission_id=mid,
                session_id=sid,
                goal=goal,
                status="FAILED",
                planner_result=planner_out,
                researcher_result=researcher_out,
                executor_result=None,
                execution_trace=trace,
                event_ids=event_ids,
                error=str(exc),
            )
