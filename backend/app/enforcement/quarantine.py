"""
Quarantine Controller — AegisMesh Phase 2

Implements ARCHITECTURE.md §21 (Enforcement Controller) — the quarantine tier.

Responsibilities:
    1. Evaluate whether an agent should be quarantined based on:
       - Trust score (< 40 → QUARANTINED tier)
       - Decision outcome (QUARANTINE from PDP)
       - Critical security event (taint hit, forged ledger, etc.)

    2. Execute quarantine:
       - Update agent status to QUARANTINED via repository
       - Emit QUARANTINE_ENFORCED event to ledger
       - Return QuarantineResult with evidence

    3. Release quarantine (admin action):
       - Update agent status to ACTIVE
       - Emit QUARANTINE_RELEASED event to ledger

The controller does NOT make policy decisions itself — it executes them.
The PDP is responsible for deciding; the controller is responsible for acting.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.decision import DecisionStatus, RiskLevel
from backend.app.schemas.event import EventCreate, EventType

logger = logging.getLogger("aegismesh.quarantine")

# Trust score below which an agent is automatically quarantined
QUARANTINE_TRUST_THRESHOLD = 40.0


@dataclass
class QuarantineResult:
    """Result of a quarantine enforcement action."""
    agent_id: str
    quarantined: bool
    reason: str
    trigger: str            # "trust_score", "pdp_decision", "taint_hit", "manual"
    event_id: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "quarantined": self.quarantined,
            "reason": self.reason,
            "trigger": self.trigger,
            "event_id": self.event_id,
            "details": self.details,
        }


class QuarantineController:
    """
    Executes quarantine and release enforcement actions.

    Injected with repository and ledger access at construction time.
    The PDP calls `maybe_quarantine` after each decision to enforce automatic
    trust-score-based quarantine.
    """

    def __init__(self, repository=None) -> None:
        self._repo = repository
        self._quarantined: Dict[str, datetime] = {}   # agent_id → quarantine timestamp
        self._lock = asyncio.Lock()

    def _get_repo(self):
        if self._repo is not None:
            return self._repo
        from backend.app.db.repository import get_repository
        return get_repository()

    # ------------------------------------------------------------------
    # Core quarantine actions
    # ------------------------------------------------------------------

    async def quarantine_agent(
        self,
        agent_id: str,
        reason: str,
        trigger: str = "pdp_decision",
        trust_score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> QuarantineResult:
        """
        Set agent status to QUARANTINED, record event in ledger.
        Idempotent — if already quarantined, returns existing result.
        """
        async with self._lock:
            repo = self._get_repo()
            agent: Optional[AgentResponse] = await repo.get_agent(agent_id)

            if agent and agent.status == AgentStatus.QUARANTINED:
                logger.debug("Agent %s already quarantined, skipping.", agent_id)
                return QuarantineResult(
                    agent_id=agent_id,
                    quarantined=True,
                    reason="Agent already in quarantine.",
                    trigger=trigger,
                    details={"existing": True},
                )

            # Update agent status
            updated = await repo.update_agent_status(agent_id, AgentStatus.QUARANTINED)
            if not updated:
                logger.error("Could not quarantine agent '%s' — not found in repository.", agent_id)
                return QuarantineResult(
                    agent_id=agent_id,
                    quarantined=False,
                    reason=f"Agent '{agent_id}' not found.",
                    trigger=trigger,
                    details={"error": "not_found"},
                )

            self._quarantined[agent_id] = datetime.now(timezone.utc)

            # Emit quarantine event to ledger
            event_id = str(uuid.uuid4())
            event_payload: Dict[str, Any] = {
                "trigger": trigger,
                "reason": reason,
                "trust_score": trust_score,
                **(details or {}),
            }

            try:
                event = EventCreate(
                    id=event_id,
                    agent_id=agent_id,
                    session_id=None,
                    event_type=EventType.STATUS_CHANGED,
                    action="agent.quarantine",
                    payload=event_payload,
                    decision={
                        "decision": DecisionStatus.QUARANTINE.value,
                        "trigger": trigger,
                    },
                )
                stored = await repo.store_event(event)
                event_id = stored.id
                logger.warning(
                    "QUARANTINE ENFORCED: agent=%s trigger=%s reason=%s",
                    agent_id, trigger, reason,
                )
            except Exception as exc:
                logger.error("Could not store quarantine event for agent %s: %s", agent_id, exc)

            return QuarantineResult(
                agent_id=agent_id,
                quarantined=True,
                reason=reason,
                trigger=trigger,
                event_id=event_id,
                details={
                    "trust_score": trust_score,
                    "quarantine_time": self._quarantined[agent_id].isoformat(),
                    **(details or {}),
                },
            )

    async def release_agent(
        self,
        agent_id: str,
        reason: str = "Manual admin release",
    ) -> QuarantineResult:
        """
        Release an agent from quarantine, restoring ACTIVE status.
        Records a QUARANTINE_RELEASED event.
        """
        async with self._lock:
            repo = self._get_repo()
            updated = await repo.update_agent_status(agent_id, AgentStatus.ACTIVE)
            if not updated:
                return QuarantineResult(
                    agent_id=agent_id,
                    quarantined=False,
                    reason=f"Agent '{agent_id}' not found — cannot release.",
                    trigger="release",
                    details={"error": "not_found"},
                )

            self._quarantined.pop(agent_id, None)

            event_id = str(uuid.uuid4())
            try:
                event = EventCreate(
                    id=event_id,
                    agent_id=agent_id,
                    session_id=None,
                    event_type=EventType.STATUS_CHANGED,
                    action="agent.quarantine.release",
                    payload={"reason": reason},
                    decision={"decision": "RELEASED"},
                )
                stored = await repo.store_event(event)
                event_id = stored.id
                logger.info("QUARANTINE RELEASED: agent=%s reason=%s", agent_id, reason)
            except Exception as exc:
                logger.error("Could not store release event for agent %s: %s", agent_id, exc)

            return QuarantineResult(
                agent_id=agent_id,
                quarantined=False,
                reason=reason,
                trigger="release",
                event_id=event_id,
                details={},
            )

    # ------------------------------------------------------------------
    # Automatic trust-score-based quarantine check
    # ------------------------------------------------------------------

    async def maybe_quarantine(
        self,
        agent_id: str,
        trust_score: float,
    ) -> Optional[QuarantineResult]:
        """
        Auto-quarantine if trust score drops into QUARANTINED tier (< 40).
        Returns None if no action taken.
        """
        if trust_score < QUARANTINE_TRUST_THRESHOLD:
            return await self.quarantine_agent(
                agent_id=agent_id,
                reason=(
                    f"Trust score {trust_score:.1f} has fallen below the quarantine "
                    f"threshold ({QUARANTINE_TRUST_THRESHOLD:.0f}). "
                    "Agent automatically isolated."
                ),
                trigger="trust_score",
                trust_score=trust_score,
            )
        return None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def is_quarantined(self, agent_id: str) -> bool:
        """Check if an agent is quarantined (repository is authoritative)."""
        async with self._lock:
            if agent_id in self._quarantined:
                return True
        # Fall back to repository for agents quarantined externally
        repo = self._get_repo()
        agent = await repo.get_agent(agent_id)
        if agent and agent.status == AgentStatus.QUARANTINED:
            return True
        return False

    async def list_quarantined(self) -> List[str]:
        """List all quarantined agents (repository is authoritative)."""
        repo = self._get_repo()
        agents = await repo.list_agents()
        return [a.id for a in agents if a.status == AgentStatus.QUARANTINED]


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_controller_instance: Optional[QuarantineController] = None


def get_quarantine_controller() -> QuarantineController:
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = QuarantineController()
    return _controller_instance


def set_quarantine_controller(controller: QuarantineController) -> None:
    global _controller_instance
    _controller_instance = controller
