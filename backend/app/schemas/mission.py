from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MissionRunRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="High-level objective provided to the mission")
    mission_id: Optional[str] = Field(None, description="Optional custom mission correlation identifier")
    session_id: Optional[str] = Field(None, description="Optional custom session identifier")


class MissionRunResponse(BaseModel):
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
