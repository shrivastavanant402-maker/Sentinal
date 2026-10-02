"""
Mission Drift Detector — AegisMesh Phase 2

Implements ARCHITECTURE.md §16 Level 1 (rule-based) drift detection.

The detector compares:
    MISSION description (from MissionContract)
    + ALLOWED tools (contract allowlist)
    + CURRENT action

and produces a drift_score (0.0 = perfect alignment, 1.0 = complete deviation).

Level 1 (Rule-based — implemented here):
    - Action is in the contract's allowed_tools → drift 0.0 (NONE)
    - Action is in forbidden_tools → drift 1.0 (CRITICAL)
    - Action is an unknown/uncategorised tool → drift 0.5 (MODERATE)
    - Action's risk level exceeds contract's maximum risk envelope → drift 0.7 (HIGH)

Level 2 (Embedding-based — stub; plug in sentence-transformers when available):
    drift_score = 1 - similarity(mission_description, action_description)

Thresholds:
    0.0 ─ 0.2   NONE
    0.2 ─ 0.5   LOW
    0.5 ─ 0.7   MODERATE
    0.7 ─ 0.9   HIGH
    0.9 ─ 1.0   CRITICAL
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from backend.app.schemas.contract import MissionContract
from backend.app.schemas.decision import ActionRequest, RiskLevel
from backend.app.policy.risk import classify_action_risk

logger = logging.getLogger("aegismesh.drift")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_THRESHOLD_NONE = 0.2
_THRESHOLD_LOW = 0.5
_THRESHOLD_MODERATE = 0.7
_THRESHOLD_HIGH = 0.9


class DriftSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_score(cls, score: float) -> "DriftSeverity":
        if score < _THRESHOLD_NONE:
            return cls.NONE
        if score < _THRESHOLD_LOW:
            return cls.LOW
        if score < _THRESHOLD_MODERATE:
            return cls.MODERATE
        if score < _THRESHOLD_HIGH:
            return cls.HIGH
        return cls.CRITICAL


@dataclass
class DriftResult:
    drift_score: float           # 0.0 (aligned) → 1.0 (deviated)
    severity: DriftSeverity
    reason: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_score": round(self.drift_score, 3),
            "severity": self.severity.value,
            "reason": self.reason,
            "details": self.details,
        }


class DriftDetector:
    """
    Rule-based mission drift detector (Level 1 per ARCHITECTURE.md §16).

    evaluate(request, contract) → DriftResult

    Designed to be called from the PDP pipeline after contract lookup.
    Returns a DriftResult; the PDP decides whether to BLOCK/APPROVAL based on
    the severity.
    """

    def evaluate(
        self,
        request: ActionRequest,
        contract: Optional[MissionContract],
    ) -> DriftResult:
        """
        Evaluate how much the requested action deviates from the agent's
        declared mission contract.
        """
        if contract is None:
            # No contract → cannot assess alignment; treat as moderate drift
            return DriftResult(
                drift_score=0.5,
                severity=DriftSeverity.MODERATE,
                reason="No active mission contract — cannot verify mission alignment.",
                details={"action": request.action, "agent_id": request.agent_id},
            )

        action = request.action

        # ── 1. Explicitly allowed ─────────────────────────────────────────
        if action in contract.allowed_tools:
            logger.debug("Drift NONE: action '%s' is explicitly allowed by contract", action)
            return DriftResult(
                drift_score=0.0,
                severity=DriftSeverity.NONE,
                reason=f"Action '{action}' is within mission contract '{contract.name}'.",
                details={"contract_id": contract.id, "action": action},
            )

        # ── 2. Explicitly forbidden ───────────────────────────────────────
        if action in contract.forbidden_tools:
            logger.warning(
                "Drift CRITICAL: action '%s' is explicitly forbidden by contract '%s'",
                action, contract.id,
            )
            return DriftResult(
                drift_score=1.0,
                severity=DriftSeverity.CRITICAL,
                reason=(
                    f"Action '{action}' is explicitly forbidden by mission contract "
                    f"'{contract.name}'. This is a critical mission drift event."
                ),
                details={"contract_id": contract.id, "action": action, "forbidden": True},
            )

        # ── 3. Risk envelope breach ───────────────────────────────────────
        action_risk = classify_action_risk(action)
        contract_max_risk = contract.risk_level

        _risk_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        action_risk_ord = _risk_order.get(action_risk, 0)
        contract_risk_ord = _risk_order.get(contract_max_risk, 1)

        if action_risk_ord > contract_risk_ord:
            drift = 0.7 + 0.1 * (action_risk_ord - contract_risk_ord)
            drift = min(drift, 0.95)
            severity = DriftSeverity.from_score(drift)
            logger.warning(
                "Drift %s: action '%s' risk=%s exceeds contract max risk=%s",
                severity.value, action, action_risk.value, contract_max_risk.value,
            )
            return DriftResult(
                drift_score=drift,
                severity=severity,
                reason=(
                    f"Action '{action}' has risk level '{action_risk.value}' which "
                    f"exceeds the contract's maximum permitted risk envelope "
                    f"'{contract_max_risk.value}'."
                ),
                details={
                    "contract_id": contract.id,
                    "action": action,
                    "action_risk": action_risk.value,
                    "contract_max_risk": contract_max_risk.value,
                },
            )

        # ── 4. Unknown/uncategorised tool not in allowlist ────────────────
        logger.info(
            "Drift MODERATE: action '%s' is not in contract allowlist (not explicitly forbidden)",
            action,
        )
        return DriftResult(
            drift_score=0.5,
            severity=DriftSeverity.MODERATE,
            reason=(
                f"Action '{action}' is not in mission contract '{contract.name}' "
                f"allowlist. Action is uncategorised — default-deny applies."
            ),
            details={
                "contract_id": contract.id,
                "action": action,
                "allowlist": contract.allowed_tools,
            },
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_detector_instance: Optional[DriftDetector] = None


def get_drift_detector() -> DriftDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = DriftDetector()
    return _detector_instance


def set_drift_detector(detector: DriftDetector) -> None:
    global _detector_instance
    _detector_instance = detector
