from typing import Any, Dict, Optional, Protocol, runtime_checkable
from backend.app.schemas.decision import ActionRequest


@runtime_checkable
class PolicyEvaluator(Protocol):
    """
    Evaluates action requests against OPA/Rego rules and runtime operational constraints.
    """
    async def evaluate_policy(self, request: ActionRequest) -> Dict[str, Any]:
        """
        Evaluates policy for action request.
        Returns: e.g. {'allowed': bool, 'status': DecisionStatus, 'reason': str}
        """
        ...


@runtime_checkable
class TrustEvaluator(Protocol):
    """
    Evaluates agent dynamic trust score, compliance tier, and minimum trust requirements.
    """
    async def evaluate_trust(self, agent_id: str, action: str) -> Dict[str, Any]:
        """
        Returns: e.g. {'trust_score': float, 'tier': str, 'sufficient': bool}
        """
        ...


@runtime_checkable
class ProvenanceEvaluator(Protocol):
    """
    Tracks data lineage, taint propagation, and secret exfiltration risks.
    """
    async def evaluate_provenance(self, request: ActionRequest) -> Dict[str, Any]:
        """
        Returns: e.g. {'taint_detected': bool, 'taint_labels': list[str], 'reason': str}
        """
        ...


@runtime_checkable
class MissionContractEvaluator(Protocol):
    """
    Validates agent actions against mission contracts, permitted tools, and parameter constraints.
    """
    async def evaluate_contract(self, request: ActionRequest) -> Dict[str, Any]:
        """
        Returns: e.g. {'valid': bool, 'violates_bounds': bool, 'reason': str}
        """
        ...


@runtime_checkable
class IdentityVerifier(Protocol):
    """
    Verifies agent Ed25519 identity, capability tokens, and cryptographic signatures.
    """
    async def verify_identity(self, agent_id: str, token_or_signature: Optional[str] = None) -> bool:
        """
        Returns: True if agent identity credentials and signatures are verified.
        """
        ...
