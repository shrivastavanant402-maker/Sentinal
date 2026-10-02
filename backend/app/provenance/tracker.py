"""
Provenance and Taint Tracker — AegisMesh Phase 2

Implements ARCHITECTURE.md §19.

Taint labels propagate from sensitive sources through agent processing
and are detected when they reach forbidden sinks.

Sensitive sources (auto-labeled):
    .env, API keys, tokens, PII, secret-labelled tool output,
    high-entropy credentials

Sensitive sinks (checked at PEP):
    external.post, git.push, shell.exec, unapproved fs.write,
    external LLM prompt, agent-to-agent message

When a tainted value reaches a forbidden sink:
    taint_hit = True
    severity   = CRITICAL
    decision   = DENY (handled by PDP integration)

The tracker also records provenance lineage so the dashboard can show:
    source -> agent -> agent -> sink
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

logger = logging.getLogger("aegismesh.provenance")

# ---------------------------------------------------------------------------
# Sensitive source patterns
# ---------------------------------------------------------------------------
_SENSITIVE_SOURCE_TOOLS: Set[str] = {
    "secrets.read",
    "env.read",
    "credentials.fetch",
    "api_key.read",
    "token.read",
    "pii.read",
    "research_db.read",  # medium — may contain sensitive records
}

_SENSITIVE_SOURCE_KEYWORDS: List[str] = [
    "secret", "api_key", "apikey", "token", "password", "credential",
    "private_key", "env", ".env", "pii", "ssn", "credit_card",
]

# ---------------------------------------------------------------------------
# Sensitive sink tools — reaching these with tainted data is a critical event
# ---------------------------------------------------------------------------
SENSITIVE_SINKS: Set[str] = {
    "external.post",
    "git.push",
    "shell.exec",
    "fs.write",          # unapproved writes
    "llm.prompt",        # external LLM calls
    "agent.message",     # agent-to-agent messages (cross-boundary propagation)
    "email.send",
    "webhook.post",
    "database.export",
}


class TaintLabel(str, Enum):
    CLEAN = "CLEAN"
    UNTRUSTED = "UNTRUSTED"       # content from external / unverified sources
    SENSITIVE = "SENSITIVE"       # content derived from secrets / PII
    TAINTED = "TAINTED"           # propagated taint (second-order)


@dataclass
class TaintRecord:
    """
    Records taint lineage for a single data flow segment.
    Used to reconstruct: source → agent → agent → sink
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: TaintLabel = TaintLabel.CLEAN
    source_tool: Optional[str] = None      # tool that produced the tainted data
    source_agent: Optional[str] = None     # agent that first handled tainted data
    propagation_path: List[str] = field(default_factory=list)   # ["agent-A", "agent-B"]
    sink_tool: Optional[str] = None        # tool being requested when taint detected
    sink_agent: Optional[str] = None       # agent requesting the sink action
    is_hit: bool = False                   # True when taint reached a sink
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label.value,
            "source_tool": self.source_tool,
            "source_agent": self.source_agent,
            "propagation_path": self.propagation_path,
            "sink_tool": self.sink_tool,
            "sink_agent": self.sink_agent,
            "is_hit": self.is_hit,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TaintCheckResult:
    is_tainted: bool = False
    label: TaintLabel = TaintLabel.CLEAN
    record: Optional[TaintRecord] = None
    reason: str = ""


class ProvenanceTracker:
    """
    Tracks data provenance and taint propagation across agent boundaries.

    Core operations:
      mark_tainted(agent_id, source_tool, payload)
          → labels data read by an agent as SENSITIVE
      check_sink(agent_id, sink_tool, payload, provenance_meta)
          → detects if tainted data is being routed to a forbidden sink
      propagate(from_agent, to_agent)
          → copies taint from sender to receiver
    """

    def __init__(self) -> None:
        # agent_id → current TaintLabel
        self._agent_taint: Dict[str, TaintLabel] = {}
        # list of all taint records (audit trail)
        self._records: List[TaintRecord] = []
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Mark agent as tainted after reading sensitive data
    # ------------------------------------------------------------------

    async def mark_tainted(
        self,
        agent_id: str,
        source_tool: str,
        payload: Optional[Dict[str, Any]] = None,
        label: TaintLabel = TaintLabel.SENSITIVE,
    ) -> TaintRecord:
        """
        Mark an agent as carrying tainted data originating from source_tool.
        Called when an ALLOW decision is returned for a sensitive source tool.
        """
        async with self._lock:
            prev = self._agent_taint.get(agent_id, TaintLabel.CLEAN)
            # Escalate if already tainted
            if label.value > prev.value or prev == TaintLabel.CLEAN:
                self._agent_taint[agent_id] = label

            record = TaintRecord(
                label=label,
                source_tool=source_tool,
                source_agent=agent_id,
                propagation_path=[agent_id],
            )
            self._records.append(record)
            logger.info(
                "Taint MARK: agent=%s source_tool=%s label=%s",
                agent_id,
                source_tool,
                label.value,
            )
            return record

    # ------------------------------------------------------------------
    # Check if taint will hit a sensitive sink
    # ------------------------------------------------------------------

    async def check_sink(
        self,
        agent_id: str,
        sink_tool: str,
        payload: Optional[Dict[str, Any]] = None,
        provenance_meta: Optional[Dict[str, Any]] = None,
    ) -> TaintCheckResult:
        """
        Check if the requesting agent carries taint AND the action is a
        sensitive sink. Returns TaintCheckResult with is_tainted=True if hit.
        """
        async with self._lock:
            current_label = self._agent_taint.get(agent_id, TaintLabel.CLEAN)

            # Check payload / provenance for taint signals from caller
            if provenance_meta:
                declared_label = provenance_meta.get("taint_label", "")
                if declared_label in (TaintLabel.SENSITIVE.value, TaintLabel.TAINTED.value):
                    current_label = TaintLabel.TAINTED
                    self._agent_taint[agent_id] = current_label

            if current_label == TaintLabel.CLEAN:
                # Also check payload keys for sensitive keywords (level-1 heuristic)
                if payload and self._payload_has_sensitive_keywords(payload):
                    current_label = TaintLabel.UNTRUSTED
                    self._agent_taint[agent_id] = current_label

            if current_label == TaintLabel.CLEAN:
                return TaintCheckResult(
                    is_tainted=False,
                    label=TaintLabel.CLEAN,
                    reason="No taint detected.",
                )

            is_sink = sink_tool in SENSITIVE_SINKS

            if is_sink:
                record = TaintRecord(
                    label=current_label,
                    source_agent=agent_id,
                    propagation_path=self._get_propagation_path(agent_id),
                    sink_tool=sink_tool,
                    sink_agent=agent_id,
                    is_hit=True,
                )
                self._records.append(record)
                logger.warning(
                    "TAINT HIT: agent=%s sink=%s label=%s — CRITICAL sink reached with tainted data",
                    agent_id,
                    sink_tool,
                    current_label.value,
                )
                return TaintCheckResult(
                    is_tainted=True,
                    label=current_label,
                    record=record,
                    reason=f"Tainted data ({current_label.value}) routed to sensitive sink '{sink_tool}'.",
                )

            # Tainted but sink is not forbidden — warn but allow (policy decides)
            return TaintCheckResult(
                is_tainted=True,
                label=current_label,
                record=None,
                reason=f"Agent carries taint ({current_label.value}) but '{sink_tool}' is not a forbidden sink.",
            )

    # ------------------------------------------------------------------
    # Cross-agent taint propagation
    # ------------------------------------------------------------------

    async def propagate(self, from_agent: str, to_agent: str) -> None:
        """
        Propagate taint label from one agent to another (cross-boundary).
        Called when a tainted agent sends a message or delegates to another.
        """
        async with self._lock:
            source_label = self._agent_taint.get(from_agent, TaintLabel.CLEAN)
            if source_label != TaintLabel.CLEAN:
                dest_label = self._agent_taint.get(to_agent, TaintLabel.CLEAN)
                if source_label.value >= dest_label.value:
                    self._agent_taint[to_agent] = TaintLabel.TAINTED
                    logger.info(
                        "Taint PROPAGATE: %s → %s (label=%s → TAINTED)",
                        from_agent,
                        to_agent,
                        source_label.value,
                    )

    # ------------------------------------------------------------------
    # Source detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_sensitive_source(tool: str) -> bool:
        """Returns True if the tool is known to produce sensitive data."""
        return tool in _SENSITIVE_SOURCE_TOOLS

    @staticmethod
    def _payload_has_sensitive_keywords(payload: Dict[str, Any]) -> bool:
        """Level-1 heuristic: check if payload keys/values contain sensitive terms."""
        flat = " ".join(str(k) + " " + str(v) for k, v in payload.items()).lower()
        return any(kw in flat for kw in _SENSITIVE_SOURCE_KEYWORDS)

    # ------------------------------------------------------------------
    # Provenance path
    # ------------------------------------------------------------------

    def _get_propagation_path(self, agent_id: str) -> List[str]:
        """Return the known propagation path for this agent from taint records."""
        for rec in reversed(self._records):
            if rec.source_agent == agent_id and not rec.is_hit:
                return rec.propagation_path + [agent_id]
        return [agent_id]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_agent_taint(self, agent_id: str) -> TaintLabel:
        async with self._lock:
            return self._agent_taint.get(agent_id, TaintLabel.CLEAN)

    async def list_taint_hits(self) -> List[TaintRecord]:
        async with self._lock:
            return [r for r in self._records if r.is_hit]

    async def all_records(self) -> List[TaintRecord]:
        async with self._lock:
            return list(self._records)

    async def clear_agent_taint(self, agent_id: str) -> None:
        """Clear taint for an agent (e.g., after quarantine + remediation)."""
        async with self._lock:
            self._agent_taint.pop(agent_id, None)
            logger.info("Taint CLEAR: agent=%s", agent_id)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_tracker_instance: Optional[ProvenanceTracker] = None


def get_provenance_tracker() -> ProvenanceTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProvenanceTracker()
    return _tracker_instance


def set_provenance_tracker(tracker: ProvenanceTracker) -> None:
    global _tracker_instance
    _tracker_instance = tracker
