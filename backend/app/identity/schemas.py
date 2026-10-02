from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class IdentityStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class IdentityVerificationStatus(str, Enum):
    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNKNOWN_AGENT = "UNKNOWN_AGENT"
    EXPIRED_REQUEST = "EXPIRED_REQUEST"
    REPLAYED_REQUEST = "REPLAYED_REQUEST"
    MALFORMED_IDENTITY = "MALFORMED_IDENTITY"


class AgentIdentity(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier")
    identity_version: int = Field(default=1, description="Identity schema/key version")
    public_key: str = Field(..., description="Ed25519 public key in hexadecimal format")
    status: IdentityStatus = Field(default=IdentityStatus.ACTIVE, description="Identity lifecycle status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IdentityVerificationResult(BaseModel):
    status: IdentityVerificationStatus
    is_valid: bool
    agent_id: str
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)
