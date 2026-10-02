from typing import Any, Dict, Optional


class SecurityError(Exception):
    """Base exception for all AegisMesh runtime security violations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        return self.message


class ActionDenied(SecurityError):
    """Raised when an agent action is blocked by PEP policy, contract, or risk evaluation."""
    pass


class AgentQuarantined(SecurityError):
    """Raised when an action is attempted by or delegated to an agent under active quarantine."""
    pass


class ApprovalRequired(SecurityError):
    """Raised when an action is high-risk and requires human administrator authorization."""
    pass


class InvalidAgentIdentity(SecurityError):
    """Raised when agent identity, capability token, or cryptographic signature is invalid or forged."""
    pass
