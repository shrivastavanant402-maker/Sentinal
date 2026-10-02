"""
Trust Engine — AegisMesh Phase 2

Implements the 4-dimension trust scoring model from ARCHITECTURE.md §20.

Dimensions:
    compliance      — did the agent comply with policy decisions?
    integrity       — is the agent's event ledger intact?
    consistency     — is the agent's behaviour consistent over time?
    claim_accuracy  — how accurate are the agent's self-reported claims?

Formula (from ARCHITECTURE.md):
    trust = 0.35 * compliance
          + 0.25 * integrity
          + 0.20 * consistency
          + 0.20 * claim_accuracy

Severity penalties (from ARCHITECTURE.md):
    LOW       -5
    MEDIUM   -15
    HIGH     -30
    CRITICAL -50

Recovery:
    +1 per 10 consecutive clean ALLOW decisions (clean_actions_since_violation)

Trust tiers:
    80-100  TRUSTED
    60-79   WATCHED
    40-59   RESTRICTED
    0-39    QUARANTINED
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from backend.app.schemas.decision import DecisionStatus, RiskLevel

logger = logging.getLogger("aegismesh.trust")

# ---------------------------------------------------------------------------
# Trust tier thresholds (ARCHITECTURE.md §20)
# ---------------------------------------------------------------------------
_TIER_TRUSTED = 80
_TIER_WATCHED = 60
_TIER_RESTRICTED = 40

# Severity → penalty mapping (ARCHITECTURE.md §20)
_SEVERITY_PENALTIES: Dict[RiskLevel, float] = {
    RiskLevel.LOW: 5.0,
    RiskLevel.MEDIUM: 15.0,
    RiskLevel.HIGH: 30.0,
    RiskLevel.CRITICAL: 50.0,
}

# After this many consecutive clean actions, restore +1 point
_RECOVERY_STRIDE = 10
_RECOVERY_DELTA = 1.0

# Dimension weights (ARCHITECTURE.md §20)
_WEIGHT_COMPLIANCE = 0.35
_WEIGHT_INTEGRITY = 0.25
_WEIGHT_CONSISTENCY = 0.20
_WEIGHT_CLAIM_ACCURACY = 0.20


class TrustTier(str, Enum):
    TRUSTED = "TRUSTED"
    WATCHED = "WATCHED"
    RESTRICTED = "RESTRICTED"
    QUARANTINED = "QUARANTINED"


@dataclass
class TrustScore:
    """Current trust state for one agent."""

    agent_id: str

    # 4 sub-dimensions — each 0..100
    compliance: float = 100.0
    integrity: float = 100.0
    consistency: float = 100.0
    claim_accuracy: float = 100.0

    # Running counters
    total_decisions: int = 0
    violations: int = 0
    consecutive_clean: int = 0  # resets on any non-ALLOW outcome

    # Computed composite (kept in sync by apply_*)
    composite: float = 100.0

    def _recalculate(self) -> None:
        """Recalculate composite from the 4 dimensions and clamp to 0..100."""
        raw = (
            _WEIGHT_COMPLIANCE * self.compliance
            + _WEIGHT_INTEGRITY * self.integrity
            + _WEIGHT_CONSISTENCY * self.consistency
            + _WEIGHT_CLAIM_ACCURACY * self.claim_accuracy
        )
        self.composite = max(0.0, min(100.0, raw))

    @property
    def tier(self) -> TrustTier:
        if self.composite >= _TIER_TRUSTED:
            return TrustTier.TRUSTED
        if self.composite >= _TIER_WATCHED:
            return TrustTier.WATCHED
        if self.composite >= _TIER_RESTRICTED:
            return TrustTier.RESTRICTED
        return TrustTier.QUARANTINED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "composite": round(self.composite, 2),
            "tier": self.tier.value,
            "compliance": round(self.compliance, 2),
            "integrity": round(self.integrity, 2),
            "consistency": round(self.consistency, 2),
            "claim_accuracy": round(self.claim_accuracy, 2),
            "total_decisions": self.total_decisions,
            "violations": self.violations,
            "consecutive_clean": self.consecutive_clean,
        }


class TrustEngine:
    """
    Thread-safe in-process trust scoring engine.

    Maintains per-agent TrustScore objects and applies updates based on
    policy decisions, integrity events, consistency observations, and
    claim verifications.
    """

    def __init__(self) -> None:
        self._scores: Dict[str, TrustScore] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Score access
    # ------------------------------------------------------------------

    async def get_score(self, agent_id: str) -> TrustScore:
        """Return current TrustScore for an agent (creates it if missing)."""
        async with self._lock:
            return self._get_or_create(agent_id)

    def _get_or_create(self, agent_id: str) -> TrustScore:
        if agent_id not in self._scores:
            self._scores[agent_id] = TrustScore(agent_id=agent_id)
        return self._scores[agent_id]

    # ------------------------------------------------------------------
    # Decision outcome application
    # ------------------------------------------------------------------

    async def apply_decision(
        self,
        agent_id: str,
        decision: DecisionStatus,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> TrustScore:
        """
        Apply a PDP decision result to the agent's trust score.

        - ALLOW → no penalty; increment consecutive_clean; trigger recovery if stride hit.
        - BLOCK / QUARANTINE → compliance penalty proportional to risk_level.
        - APPROVAL → no penalty; treated as neutral.
        """
        async with self._lock:
            score = self._get_or_create(agent_id)
            score.total_decisions += 1

            if decision == DecisionStatus.ALLOW:
                score.consecutive_clean += 1
                # Recovery: +1 per 10 consecutive clean decisions
                if score.consecutive_clean % _RECOVERY_STRIDE == 0:
                    penalty = _SEVERITY_PENALTIES.get(risk_level, 0.0)
                    score.compliance = min(100.0, score.compliance + _RECOVERY_DELTA)
                    score.consistency = min(100.0, score.consistency + _RECOVERY_DELTA)
                    logger.debug(
                        "Trust recovery for %s: +%.1f (consecutive_clean=%d)",
                        agent_id,
                        _RECOVERY_DELTA,
                        score.consecutive_clean,
                    )

            elif decision in (DecisionStatus.BLOCK, DecisionStatus.QUARANTINE):
                score.violations += 1
                score.consecutive_clean = 0  # reset recovery streak
                penalty = _SEVERITY_PENALTIES.get(risk_level, 5.0)
                score.compliance = max(0.0, score.compliance - penalty)
                logger.info(
                    "Trust penalty for %s: -%.1f compliance (decision=%s, risk=%s → tier=%s)",
                    agent_id,
                    penalty,
                    decision.value,
                    risk_level.value,
                    score.tier.value,
                )

            elif decision == DecisionStatus.APPROVAL:
                # Approval required is a neutral signal — not a violation
                pass

            score._recalculate()
            return score

    # ------------------------------------------------------------------
    # Integrity update
    # ------------------------------------------------------------------

    async def apply_integrity_violation(
        self,
        agent_id: str,
        severity: RiskLevel = RiskLevel.HIGH,
    ) -> TrustScore:
        """
        Apply an integrity dimension penalty (e.g., ledger tamper detected,
        forged event, hash mismatch).
        """
        async with self._lock:
            score = self._get_or_create(agent_id)
            penalty = _SEVERITY_PENALTIES.get(severity, 30.0)
            score.integrity = max(0.0, score.integrity - penalty)
            score.violations += 1
            score.consecutive_clean = 0
            score._recalculate()
            logger.warning(
                "Integrity violation for %s: -%.1f integrity (severity=%s → tier=%s)",
                agent_id,
                penalty,
                severity.value,
                score.tier.value,
            )
            return score

    # ------------------------------------------------------------------
    # Claim accuracy update
    # ------------------------------------------------------------------

    async def apply_false_claim(
        self,
        agent_id: str,
        severity: RiskLevel = RiskLevel.MEDIUM,
    ) -> TrustScore:
        """
        Apply a claim_accuracy penalty when an agent makes a false claim
        (ARCHITECTURE.md §25).
        """
        async with self._lock:
            score = self._get_or_create(agent_id)
            penalty = _SEVERITY_PENALTIES.get(severity, 15.0)
            score.claim_accuracy = max(0.0, score.claim_accuracy - penalty)
            score._recalculate()
            logger.warning(
                "False claim penalty for %s: -%.1f claim_accuracy → composite=%.1f",
                agent_id,
                penalty,
                score.composite,
            )
            return score

    # ------------------------------------------------------------------
    # Consistency update
    # ------------------------------------------------------------------

    async def apply_consistency_violation(
        self,
        agent_id: str,
        severity: RiskLevel = RiskLevel.MEDIUM,
    ) -> TrustScore:
        """
        Apply a consistency penalty (e.g., anomalous call rate, mission drift
        pattern).
        """
        async with self._lock:
            score = self._get_or_create(agent_id)
            penalty = _SEVERITY_PENALTIES.get(severity, 15.0)
            score.consistency = max(0.0, score.consistency - penalty)
            score._recalculate()
            logger.info(
                "Consistency violation for %s: -%.1f consistency → tier=%s",
                agent_id,
                penalty,
                score.tier.value,
            )
            return score

    # ------------------------------------------------------------------
    # Bulk reset (testing / admin)
    # ------------------------------------------------------------------

    async def reset_score(self, agent_id: str) -> TrustScore:
        """Reset an agent's trust score back to 100/100/100/100."""
        async with self._lock:
            self._scores[agent_id] = TrustScore(agent_id=agent_id)
            return self._scores[agent_id]

    async def all_scores(self) -> Dict[str, TrustScore]:
        async with self._lock:
            return dict(self._scores)

    def get_composite_score(self, agent_id: str) -> float:
        """
        Synchronous fast-path for composite score lookup (used by PDP).
        Returns 100.0 if agent not yet tracked.
        """
        score = self._scores.get(agent_id)
        return score.composite if score else 100.0


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_trust_engine_instance: Optional[TrustEngine] = None


def get_trust_engine() -> TrustEngine:
    global _trust_engine_instance
    if _trust_engine_instance is None:
        _trust_engine_instance = TrustEngine()
    return _trust_engine_instance


def set_trust_engine(engine: TrustEngine) -> None:
    global _trust_engine_instance
    _trust_engine_instance = engine
