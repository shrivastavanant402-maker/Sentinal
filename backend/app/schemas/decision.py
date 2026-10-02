from enum import Enum
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    APPROVAL = "APPROVAL"
    QUARANTINE = "QUARANTINE"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionReason(str, Enum):
    ALLOWED_BY_POLICY = "ALLOWED_BY_POLICY"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    MISSION_DRIFT = "MISSION_DRIFT"
    TAINT_SENSITIVE_LEAK = "TAINT_SENSITIVE_LEAK"
    INSUFFICIENT_TRUST = "INSUFFICIENT_TRUST"
    HIGH_RISK_ACTION = "HIGH_RISK_ACTION"
    AGENT_QUARANTINED = "AGENT_QUARANTINED"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    UNKNOWN = "UNKNOWN"


class ActionRequest(BaseModel):
    agent_id: str = Field(..., description="ID of agent requesting action execution")
    action: str = Field(..., description="Action/tool name, e.g. web.search, database.export")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action arguments and parameters")
    mission_id: Optional[str] = Field(None, description="Optional mission context identifier")
    session_id: Optional[str] = Field(None, description="Optional session context identifier")
    provenance: Optional[Dict[str, Any]] = Field(None, description="Optional taint and lineage metadata")
    # ── Identity proof (Step 7) ───────────────────────────────────────────────
    signature: Optional[str] = Field(None, description="Ed25519 signature (hex) over canonical message")
    timestamp: Optional[float] = Field(None, description="Unix epoch float when the request was signed")
    nonce: Optional[str] = Field(None, description="Unique per-request identifier for anti-replay protection")


class DecisionResponse(BaseModel):
    decision: DecisionStatus = Field(..., description="PEP enforcement outcome")
    allowed: bool = Field(..., description="Whether action is permitted to proceed")
    reason: Union[DecisionReason, str] = Field(DecisionReason.ALLOWED_BY_POLICY, description="Rationale for decision")
    risk_level: RiskLevel = Field(RiskLevel.LOW, description="Assessed risk level")
    agent_id: str = Field(..., description="Subject agent ID")
    action: str = Field(..., description="Evaluated action/tool name")
    event_id: Optional[str] = Field(None, description="Ledger event ID if event was recorded")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual facts or obligation details")
