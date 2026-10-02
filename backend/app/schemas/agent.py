from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    HALTED = "halted"
    QUARANTINED = "quarantined"


class AgentCreate(BaseModel):
    id: str = Field(..., description="Unique agent identifier (e.g. planner-01)")
    name: str = Field(..., description="Display name for the agent")
    role: str = Field(..., description="Role of the agent (e.g. planner, researcher, executor)")
    public_key: Optional[str] = Field(None, description="Optional public key for signature verification")
    capabilities: List[str] = Field(default_factory=list, description="Allowed capabilities or tools")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary agent metadata")


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    status: AgentStatus = AgentStatus.ACTIVE
    trust_score: float = 100.0
    public_key: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
