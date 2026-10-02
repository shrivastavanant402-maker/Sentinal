from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.alert import AlertResponse
from backend.app.schemas.decision import DecisionStatus, RiskLevel


class AttackScenario(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SECRET_EXFILTRATION = "secret_exfiltration"
    ROGUE_AGENT = "rogue_agent"


class AttackSimulateRequest(BaseModel):
    agent_id: str = Field(..., description="Target agent identifier")
    scenario: AttackScenario = Field(..., description="Attack scenario to execute")


class AttackSimulateResponse(BaseModel):
    scenario: AttackScenario = Field(..., description="Executed attack scenario")
    agent_id: str = Field(..., description="Target agent identifier")
    target_agent_id: Optional[str] = Field(None, description="Alias for target agent identifier")
    status: str = Field("completed", description="Simulation status (completed, failed)")
    decision: DecisionStatus = Field(..., description="Enforcement decision: ALLOW, BLOCK, QUARANTINE, APPROVAL")
    allowed: bool = Field(..., description="Whether action was permitted")
    reason: str = Field(..., description="Decision rationale")
    risk_level: RiskLevel = Field(..., description="Assessed risk level")
    enforcement_outcome: str = Field(..., description="Human-readable enforcement outcome")
    action: str = Field(..., description="Evaluated action/tool name")
    event_id: Optional[str] = Field(None, description="Associated ledger event ID")
    alert: Optional[AlertResponse] = Field(None, description="Generated alert if blocked/quarantined")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual diagnostic details")
    trust_delta: Optional[float] = Field(None, description="Trust delta if modified by runtime engine")
    message: str = Field(..., description="Scenario summary message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of execution")

    model_config = {
        "from_attributes": True
    }
