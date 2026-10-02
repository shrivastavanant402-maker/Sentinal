from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCreate(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = Field(None, description="Associated agent ID")
    event_id: Optional[str] = Field(None, description="Associated event ID")
    severity: AlertSeverity = AlertSeverity.MEDIUM
    alert_type: str = Field(..., description="Category of the alert")
    message: str = Field(..., description="Human-readable alert message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic context")


class AlertResponse(BaseModel):
    id: str
    agent_id: Optional[str] = None
    event_id: Optional[str] = None
    severity: AlertSeverity
    alert_type: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
