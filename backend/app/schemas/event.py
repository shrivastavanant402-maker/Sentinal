from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class EventType(str, Enum):
    AGENT_REGISTERED = "agent_registered"
    PLAN_DECLARED = "plan_declared"
    TOOL_CALL_REQUEST = "tool_call_request"
    TOOL_CALL_RESPONSE = "tool_call_response"
    STATUS_CHANGED = "status_changed"
    ALERT_TRIGGERED = "alert_triggered"
    ENFORCEMENT = "enforcement"


class EventCreate(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = Field(..., description="ID of the agent generating the event")
    session_id: Optional[str] = Field(None, description="Optional session or mission ID")
    event_type: str = Field(..., description="Type of event, e.g. plan_declared or tool_call_request")
    action: str = Field(..., description="Specific action, e.g. web.search, plan.create, report.generate")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")
    decision: Dict[str, Any] = Field(default_factory=dict, description="PEP evaluation decision (allowed, denied, etc.)")
    agent_signature: Optional[str] = Field(None, description="Cryptographic signature from the agent")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventResponse(BaseModel):
    id: str
    seq: int
    timestamp: datetime
    agent_id: str
    session_id: Optional[str] = None
    event_type: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
    previous_hash: str
    content_hash: str
    event_hash: str
    agent_signature: Optional[str] = None
    core_signature: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
