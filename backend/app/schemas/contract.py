from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.decision import RiskLevel


class MissionContract(BaseModel):
    """
    Strongly-typed runtime mission contract defining authorization bounds
    for an autonomous agent within a specific mission context.
    """
    id: str = Field(..., description="Unique contract identifier, e.g. contract-researcher-v1")
    mission_id: Optional[str] = Field(None, description="Optional mission context identifier")
    agent_id: str = Field(..., description="Target agent subject to this contract")
    name: str = Field(..., description="Human-readable contract name")
    description: str = Field(default="", description="Description of mission purpose and constraints")
    allowed_tools: List[str] = Field(default_factory=list, description="Explicitly permitted actions/tools")
    forbidden_tools: List[str] = Field(default_factory=list, description="Explicitly prohibited actions/tools")
    allowed_resources: List[str] = Field(default_factory=list, description="Allowed resources, endpoints, or datasets")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Maximum permitted risk envelope")
    enabled: bool = Field(default=True, description="Whether contract is actively enforced")
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, v: Any) -> RiskLevel:
        if isinstance(v, RiskLevel):
            return v
        if isinstance(v, str):
            val = v.lower()
            try:
                return RiskLevel(val)
            except ValueError:
                return RiskLevel.MEDIUM
        return RiskLevel.MEDIUM

    model_config = {
        "from_attributes": True
    }


class ContractCreate(BaseModel):
    """Payload to create or register a mission contract."""
    id: Optional[str] = Field(None, description="Optional custom ID; generated if omitted")
    mission_id: Optional[str] = Field(None, description="Optional mission ID")
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Contract name")
    description: str = Field(default="")
    allowed_tools: List[str] = Field(default_factory=list)
    forbidden_tools: List[str] = Field(default_factory=list)
    allowed_resources: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    enabled: bool = Field(default=True)

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, v: Any) -> RiskLevel:
        if isinstance(v, RiskLevel):
            return v
        if isinstance(v, str):
            val = v.lower()
            try:
                return RiskLevel(val)
            except ValueError:
                return RiskLevel.MEDIUM
        return RiskLevel.MEDIUM


class ContractUpdate(BaseModel):
    """Payload to update an existing mission contract."""
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    forbidden_tools: Optional[List[str]] = None
    allowed_resources: Optional[List[str]] = None
    risk_level: Optional[RiskLevel] = None
    enabled: Optional[bool] = None

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, v: Any) -> Optional[RiskLevel]:
        if v is None:
            return None
        if isinstance(v, RiskLevel):
            return v
        if isinstance(v, str):
            val = v.lower()
            try:
                return RiskLevel(val)
            except ValueError:
                return RiskLevel.MEDIUM
        return RiskLevel.MEDIUM
