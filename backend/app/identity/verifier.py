import logging
import time
from typing import Any, Dict, Optional

from backend.app.config import get_settings
from backend.app.identity.crypto import create_canonical_message, verify_ed25519_signature
from backend.app.identity.replay import ReplayCache, get_replay_cache
from backend.app.identity.schemas import (
    IdentityVerificationResult,
    IdentityVerificationStatus,
)
from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.decision import ActionRequest

logger = logging.getLogger("aegismesh.identity.verifier")

# Default clock skew tolerance: 300 seconds (5 minutes)
MAX_CLOCK_SKEW_SECONDS = 300.0


class IdentityVerifier:
    """
    Dedicated cryptographic identity verifier.
    Enforces Ed25519 signature verification, freshness, and anti-replay protection.
    """

    def __init__(
        self,
        replay_cache: Optional[ReplayCache] = None,
        clock_skew_seconds: float = MAX_CLOCK_SKEW_SECONDS,
        strict_signatures: Optional[bool] = None,
    ):
        self.replay_cache = replay_cache or get_replay_cache()
        self.clock_skew_seconds = clock_skew_seconds
        self.strict_signatures = strict_signatures

    def _is_strict_mode(self) -> bool:
        if self.strict_signatures is not None:
            return self.strict_signatures
        settings = get_settings()
        return getattr(settings, "REQUIRE_AGENT_SIGNATURES", False)

    async def verify(
        self,
        request: ActionRequest,
        agent: Optional[AgentResponse] = None,
        current_time: Optional[float] = None,
    ) -> IdentityVerificationResult:
        """
        Verifies identity of an action request against the registered agent material.
        Never executes action. Fails closed on any inconsistency or signature mismatch.
        """
        now = time.time() if current_time is None else current_time

        # ── 1. Unknown Agent Check ──────────────────────────────────────────
        if agent is None:
            logger.warning(
                "Identity verification failed: Unregistered agent '%s'",
                request.agent_id,
            )
            return IdentityVerificationResult(
                status=IdentityVerificationStatus.UNKNOWN_AGENT,
                is_valid=False,
                agent_id=request.agent_id,
                reason="Agent is not registered. Anonymous actions are strictly prohibited.",
                details={"agent_id": request.agent_id},
            )

        public_key = agent.public_key
        has_registered_key = bool(public_key and str(public_key).strip())

        # If strict mode is enabled, every agent must have a registered public key
        if self._is_strict_mode() and not has_registered_key:
            logger.warning("Strict identity mode active: Agent '%s' has no registered public key", request.agent_id)
            return IdentityVerificationResult(
                status=IdentityVerificationStatus.MALFORMED_IDENTITY,
                is_valid=False,
                agent_id=request.agent_id,
                reason=f"Agent '{request.agent_id}' does not have a registered cryptographic public key.",
                details={"agent_id": request.agent_id},
            )

        # ── 2. Cryptographic Signature & Freshness Checks ───────────────────
        # If the agent has a registered public key, or the request contains a signature:
        # Cryptographic verification is strictly required and enforced.
        if has_registered_key or request.signature:
            if not has_registered_key:
                logger.warning("Signature provided but agent '%s' has no public key registered", request.agent_id)
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.MALFORMED_IDENTITY,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason=f"Signature provided but agent '{request.agent_id}' has no public key registered.",
                )

            if not request.signature:
                logger.warning(
                    "Missing signature: Agent '%s' is registered with Ed25519 identity but submitted unsigned request",
                    request.agent_id,
                )
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.INVALID_SIGNATURE,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason=f"Agent '{request.agent_id}' has registered cryptographic identity; signature is required.",
                )

            # Check timestamp presence
            if request.timestamp is None:
                logger.warning("Malformed identity: missing timestamp on signed request from '%s'", request.agent_id)
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.MALFORMED_IDENTITY,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason="Signed action request is missing timestamp.",
                )

            # Check nonce presence
            if not request.nonce:
                logger.warning("Malformed identity: missing nonce on signed request from '%s'", request.agent_id)
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.MALFORMED_IDENTITY,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason="Signed action request is missing nonce identifier.",
                )

            # Check timestamp expiration / clock skew
            age = abs(now - float(request.timestamp))
            if age > self.clock_skew_seconds:
                logger.warning(
                    "Expired request: agent='%s' age=%.1fs exceeds tolerance=%.1fs",
                    request.agent_id,
                    age,
                    self.clock_skew_seconds,
                )
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.EXPIRED_REQUEST,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason=f"Request timestamp expired (age={age:.1f}s, max_skew={self.clock_skew_seconds}s).",
                    details={"timestamp": request.timestamp, "now": now, "age": age},
                )

            # Check anti-replay
            fresh = await self.replay_cache.check_and_record(
                nonce=request.nonce,
                request_timestamp=float(request.timestamp),
                now=now,
            )
            if not fresh:
                logger.warning("Replay protection: Nonce '%s' from agent '%s' already used", request.nonce, request.agent_id)
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.REPLAYED_REQUEST,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason=f"Request nonce '{request.nonce}' was already consumed. Replay rejected.",
                    details={"nonce": request.nonce},
                )

            # Canonical message reconstruction & signature verification
            canonical_msg = create_canonical_message(
                agent_id=request.agent_id,
                action=request.action,
                payload=request.payload or {},
                mission_id=request.mission_id,
                timestamp=float(request.timestamp),
                nonce=request.nonce,
            )

            is_sig_valid = verify_ed25519_signature(
                public_key_hex=str(public_key),
                message=canonical_msg,
                signature_hex=str(request.signature),
            )

            if not is_sig_valid:
                logger.warning(
                    "Invalid signature for agent '%s' on action '%s'",
                    request.agent_id,
                    request.action,
                )
                return IdentityVerificationResult(
                    status=IdentityVerificationStatus.INVALID_SIGNATURE,
                    is_valid=False,
                    agent_id=request.agent_id,
                    reason=f"Ed25519 signature verification failed for agent '{request.agent_id}'.",
                    details={"agent_id": request.agent_id, "action": request.action},
                )

        # ── 3. Identity Confirmed ───────────────────────────────────────────
        logger.debug("Identity verification VALID for agent '%s'", request.agent_id)
        return IdentityVerificationResult(
            status=IdentityVerificationStatus.VALID,
            is_valid=True,
            agent_id=request.agent_id,
            reason="Identity verified successfully.",
            details={"has_cryptographic_signature": bool(request.signature)},
        )


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

_verifier_instance: Optional[IdentityVerifier] = None


def get_identity_verifier() -> IdentityVerifier:
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = IdentityVerifier()
    return _verifier_instance


def set_identity_verifier(verifier: IdentityVerifier) -> None:
    global _verifier_instance
    _verifier_instance = verifier
