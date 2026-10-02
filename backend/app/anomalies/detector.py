from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.db.repository import BaseRepository, get_repository
from backend.app.schemas.alert import AlertCreate, AlertResponse, AlertSeverity
from backend.app.schemas.anomaly import DetectedAnomaly, AnomalyDetectResponse
from backend.app.schemas.event import EventResponse

logger = logging.getLogger("aegismesh.anomalies")


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def find_window_match(
    events: List[EventResponse],
    window_seconds: float,
    min_events: int,
) -> Optional[List[EventResponse]]:
    """
    Finds the most recent sliding window of events within `window_seconds`
    that contains at least `min_events`.
    Returns the matching events ordered from oldest to newest, or None.
    """
    if len(events) < min_events:
        return None

    # Inspect from the newest event backwards to capture the most recent window
    for i in range(len(events) - 1, min_events - 2, -1):
        end_event = events[i]
        end_ts = to_utc(end_event.timestamp).timestamp()
        window_events = []
        for j in range(i, -1, -1):
            cand_ts = to_utc(events[j].timestamp).timestamp()
            if end_ts - cand_ts <= window_seconds:
                window_events.append(events[j])
            else:
                break
        if len(window_events) >= min_events:
            # window_events was collected newest-first; reverse to chronological
            return list(reversed(window_events))
    return None


class AnomalyDetector:
    """
    Deterministic runtime anomaly detection engine for AegisMesh.
    Evaluates recorded ledger events against three strict rules:
      - Rule A: Repeated High-Risk Actions (>= 3 high/critical actions within 5 minutes)
      - Rule B: Repeated Policy Violations (>= 3 block/quarantine violations within 5 minutes)
      - Rule C: Action Burst / Behavioral Spike (>= 10 actions within 1 minute)
    
    Deduplicates alerts deterministically so repeated queries never generate duplicate alerts.
    Strictly read-only with respect to security enforcement: never alters PEP, trust, or contracts.
    """

    def __init__(self, repository: Optional[BaseRepository] = None):
        self._repo = repository

    def _get_repo(self) -> BaseRepository:
        return self._repo or get_repository()

    @staticmethod
    def is_high_risk_event(event: EventResponse) -> bool:
        """Rule A predicate: event has high or critical risk assessment."""
        decision = event.decision or {}
        risk = str(decision.get("risk_level") or "").lower()
        return risk in ("high", "critical")

    @staticmethod
    def is_policy_violation_event(event: EventResponse) -> bool:
        """Rule B predicate: event resulted in a BLOCK or QUARANTINE policy verdict."""
        if event.event_type != "enforcement":
            return False
        decision = event.decision or {}
        status_val = str(decision.get("status") or decision.get("decision") or "").upper()
        allowed = decision.get("allowed")
        return status_val in ("BLOCK", "QUARANTINE") or allowed is False

    async def detect_anomalies(
        self,
        agent_id: Optional[str] = None,
        window_seconds: int = 300,
    ) -> AnomalyDetectResponse:
        repo = self._get_repo()

        # 1. Validate agent if explicitly specified
        if agent_id:
            agent = await repo.get_agent(agent_id)
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent '{agent_id}' not found",
                )
            agents_to_scan = [agent_id]
        else:
            all_agents = await repo.list_agents()
            agents_to_scan = sorted([a.id for a in all_agents])

        # 2. Fetch all events and alerts
        all_events = await repo.list_events(limit=10000, offset=0)
        existing_alerts = await repo.list_alerts(limit=1000)

        # If scanning all agents, also include any agent_id appearing in events
        if not agent_id:
            found_ids = set(agents_to_scan)
            for ev in all_events:
                if ev.agent_id:
                    found_ids.add(ev.agent_id)
            agents_to_scan = sorted(list(found_ids))

        # Group events by agent_id and sort chronologically
        agent_events: Dict[str, List[EventResponse]] = {}
        for ev in all_events:
            agent_events.setdefault(ev.agent_id, []).append(ev)
        for aid in agent_events:
            agent_events[aid].sort(key=lambda e: (to_utc(e.timestamp), e.seq))

        detected_list: List[DetectedAnomaly] = []
        new_alerts_count = 0
        deduplicated_alerts_count = 0

        # Helper to check if an alert for this agent + anomaly_type + latest_event already exists
        def find_existing_alert(aid: str, alert_type: str, latest_ev_id: str) -> Optional[AlertResponse]:
            for a in existing_alerts:
                if a.agent_id == aid and a.alert_type == alert_type:
                    if str(a.event_id) == latest_ev_id or str(a.details.get("latest_event_id")) == latest_ev_id:
                        return a
            return None

        # 3. Evaluate rules per agent
        for aid in agents_to_scan:
            events = agent_events.get(aid, [])
            if not events:
                continue

            # ── RULE A: Repeated High-Risk Activity ────────────────────────────
            high_risk_events = [e for e in events if self.is_high_risk_event(e)]
            rule_a_match = find_window_match(
                high_risk_events,
                window_seconds=float(window_seconds),
                min_events=3,
            )
            if rule_a_match:
                latest_ev = rule_a_match[-1]
                count = len(rule_a_match)
                time_span = (to_utc(latest_ev.timestamp) - to_utc(rule_a_match[0].timestamp)).total_seconds()
                existing = find_existing_alert(aid, "REPEATED_HIGH_RISK_ACTIVITY", latest_ev.id)
                event_ids = [e.id for e in rule_a_match]

                if existing:
                    deduplicated_alerts_count += 1
                    detected_list.append(
                        DetectedAnomaly(
                            anomaly_type="REPEATED_HIGH_RISK_ACTIVITY",
                            agent_id=aid,
                            severity=AlertSeverity.HIGH,
                            rule_name="Rule A - Repeated High-Risk Activity",
                            message=existing.message,
                            explanation="Triggered when the same agent produces >= 3 high or critical risk events within 5 minutes.",
                            event_count=count,
                            triggering_event_ids=event_ids,
                            supporting_event_ids=event_ids,
                            latest_event_id=latest_ev.id,
                            alert_id=existing.id,
                            created_alert=False,
                            timestamp=existing.created_at,
                        )
                    )
                else:
                    msg = (
                        f"Repeated high-risk activity detected: Agent '{aid}' performed "
                        f"{count} high/critical actions within {int(time_span)}s."
                    )
                    details = {
                        "anomaly_rule": "Rule A - Repeated High-Risk Actions",
                        "event_count": count,
                        "time_span_seconds": time_span,
                        "triggering_event_ids": event_ids,
                        "supporting_event_ids": event_ids,
                        "latest_event_id": latest_ev.id,
                        "actions": [e.action for e in rule_a_match],
                        "risk_levels": [e.decision.get("risk_level") for e in rule_a_match],
                    }
                    new_alert = await repo.store_alert(
                        AlertCreate(
                            agent_id=aid,
                            event_id=latest_ev.id,
                            severity=AlertSeverity.HIGH,
                            alert_type="REPEATED_HIGH_RISK_ACTIVITY",
                            message=msg,
                            details=details,
                        )
                    )
                    existing_alerts.append(new_alert)
                    new_alerts_count += 1
                    detected_list.append(
                        DetectedAnomaly(
                            anomaly_type="REPEATED_HIGH_RISK_ACTIVITY",
                            agent_id=aid,
                            severity=AlertSeverity.HIGH,
                            rule_name="Rule A - Repeated High-Risk Activity",
                            message=msg,
                            explanation="Triggered when the same agent produces >= 3 high or critical risk events within 5 minutes.",
                            event_count=count,
                            triggering_event_ids=event_ids,
                            supporting_event_ids=event_ids,
                            latest_event_id=latest_ev.id,
                            alert_id=new_alert.id,
                            created_alert=True,
                            timestamp=new_alert.created_at,
                        )
                    )

            # ── RULE B: Repeated Policy Violations ─────────────────────────────
            violation_events = [e for e in events if self.is_policy_violation_event(e)]
            rule_b_match = find_window_match(
                violation_events,
                window_seconds=float(window_seconds),
                min_events=3,
            )
            if rule_b_match:
                latest_ev = rule_b_match[-1]
                count = len(rule_b_match)
                time_span = (to_utc(latest_ev.timestamp) - to_utc(rule_b_match[0].timestamp)).total_seconds()
                existing = find_existing_alert(aid, "REPEATED_POLICY_VIOLATIONS", latest_ev.id)
                event_ids = [e.id for e in rule_b_match]

                if existing:
                    deduplicated_alerts_count += 1
                    detected_list.append(
                        DetectedAnomaly(
                            anomaly_type="REPEATED_POLICY_VIOLATIONS",
                            agent_id=aid,
                            severity=AlertSeverity.HIGH,
                            rule_name="Rule B - Repeated Policy Violations",
                            message=existing.message,
                            explanation="Triggered when the same agent incurs >= 3 blocked or quarantined enforcement violations within 5 minutes.",
                            event_count=count,
                            triggering_event_ids=event_ids,
                            supporting_event_ids=event_ids,
                            latest_event_id=latest_ev.id,
                            alert_id=existing.id,
                            created_alert=False,
                            timestamp=existing.created_at,
                        )
                    )
                else:
                    msg = (
                        f"Repeated policy violations detected: Agent '{aid}' accumulated "
                        f"{count} blocked/quarantined enforcement violations within {int(time_span)}s."
                    )
                    details = {
                        "anomaly_rule": "Rule B - Repeated Policy Violations",
                        "event_count": count,
                        "time_span_seconds": time_span,
                        "triggering_event_ids": event_ids,
                        "supporting_event_ids": event_ids,
                        "latest_event_id": latest_ev.id,
                        "actions": [e.action for e in rule_b_match],
                        "reasons": [e.decision.get("reason") for e in rule_b_match],
                    }
                    new_alert = await repo.store_alert(
                        AlertCreate(
                            agent_id=aid,
                            event_id=latest_ev.id,
                            severity=AlertSeverity.HIGH,
                            alert_type="REPEATED_POLICY_VIOLATIONS",
                            message=msg,
                            details=details,
                        )
                    )
                    existing_alerts.append(new_alert)
                    new_alerts_count += 1
                    detected_list.append(
                        DetectedAnomaly(
                            anomaly_type="REPEATED_POLICY_VIOLATIONS",
                            agent_id=aid,
                            severity=AlertSeverity.HIGH,
                            rule_name="Rule B - Repeated Policy Violations",
                            message=msg,
                            explanation="Triggered when the same agent incurs >= 3 blocked or quarantined enforcement violations within 5 minutes.",
                            event_count=count,
                            triggering_event_ids=event_ids,
                            supporting_event_ids=event_ids,
                            latest_event_id=latest_ev.id,
                            alert_id=new_alert.id,
                            created_alert=True,
                            timestamp=new_alert.created_at,
                        )
                    )

            # ── RULE C: Action Burst / Behavioral Spike ───────────────────────
            # >= 10 events within 60 seconds (1 minute)
            rule_c_match = find_window_match(
                events,
                window_seconds=60.0,
                min_events=10,
            )
            if rule_c_match:
                latest_ev = rule_c_match[-1]
                count = len(rule_c_match)
                time_span = (to_utc(latest_ev.timestamp) - to_utc(rule_c_match[0].timestamp)).total_seconds()
                existing = find_existing_alert(aid, "ACTION_BURST_ANOMALY", latest_ev.id)
                event_ids = [e.id for e in rule_c_match]

                if existing:
                    deduplicated_alerts_count += 1
                    detected_list.append(
                        DetectedAnomaly(
                            anomaly_type="ACTION_BURST_ANOMALY",
                            agent_id=aid,
                            severity=AlertSeverity.MEDIUM,
                            rule_name="Rule C - Action Burst / Behavioral Spike",
                            message=existing.message,
                            explanation="Triggered when an agent executes >= 10 actions within 1 minute, indicating runaway automated execution.",
                            event_count=count,
                            triggering_event_ids=event_ids,
                            supporting_event_ids=event_ids,
                            latest_event_id=latest_ev.id,
                            alert_id=existing.id,
                            created_alert=False,
                            timestamp=existing.created_at,
                        )
                    )
                else:
                    msg = (
                        f"Action burst anomaly detected: Agent '{aid}' executed "
                        f"{count} actions within {int(time_span)}s, indicating automated/uncontrolled execution."
                    )
                    details = {
                        "anomaly_rule": "Rule C - Action Burst / Behavioral Spike",
                        "event_count": count,
                        "time_span_seconds": time_span,
                        "triggering_event_ids": event_ids,
                        "supporting_event_ids": event_ids,
                        "latest_event_id": latest_ev.id,
                        "actions": [e.action for e in rule_c_match],
                    }
                    new_alert = await repo.store_alert(
                        AlertCreate(
                            agent_id=aid,
                            event_id=latest_ev.id,
                            severity=AlertSeverity.MEDIUM,
                            alert_type="ACTION_BURST_ANOMALY",
                            message=msg,
                            details=details,
                        )
                    )
                    existing_alerts.append(new_alert)
                    new_alerts_count += 1
                    detected_list.append(
                        DetectedAnomaly(
                            anomaly_type="ACTION_BURST_ANOMALY",
                            agent_id=aid,
                            severity=AlertSeverity.MEDIUM,
                            rule_name="Rule C - Action Burst / Behavioral Spike",
                            message=msg,
                            explanation="Triggered when an agent executes >= 10 actions within 1 minute, indicating runaway automated execution.",
                            event_count=count,
                            triggering_event_ids=event_ids,
                            supporting_event_ids=event_ids,
                            latest_event_id=latest_ev.id,
                            alert_id=new_alert.id,
                            created_alert=True,
                            timestamp=new_alert.created_at,
                        )
                    )

        relevant_event_ids = list(dict.fromkeys([eid for a in detected_list for eid in a.triggering_event_ids]))

        return AnomalyDetectResponse(
            scanned_agents=agents_to_scan,
            total_events_analyzed=len(all_events),
            rules_evaluated=[
                "Rule A: Repeated High-Risk Activity (>= 3 high/crit in 5m)",
                "Rule B: Repeated Policy Violations (>= 3 block/quarantine in 5m)",
                "Rule C: Action Burst / Behavioral Spike (>= 10 actions in 1m)",
            ],
            anomalies_detected=len(detected_list),
            alerts_created=new_alerts_count,
            new_alerts_created=new_alerts_count,
            alerts_deduplicated=deduplicated_alerts_count,
            relevant_event_ids=relevant_event_ids,
            anomalies=detected_list,
        )


_detector_instance: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
    return _detector_instance
