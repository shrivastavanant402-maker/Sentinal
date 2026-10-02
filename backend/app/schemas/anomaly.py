from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.alert import AlertSeverity


class AnomalyDetectRequest(BaseModel):
    agent_id: Optional[str] = Field(None, description="Optional agent ID to target. If omitted, scans all agents.")
    window_seconds: Optional[int] = Field(300, description="Rolling time window in seconds for evaluation (default 300s)")


class DetectedAnomaly(BaseModel):
    anomaly_type: str = Field(..., description="Anomaly classification code")
    agent_id: str = Field(..., description="Agent that produced the anomalous pattern")
    severity: AlertSeverity = Field(..., description="Assessed anomaly severity")
    rule_name: str = Field(..., description="Name of the deterministic rule that triggered")
    message: str = Field(..., description="Human-readable explanation of the pattern")
    explanation: Optional[str] = Field(None, description="Detailed explanation of the rule threshold")
    event_count: int = Field(..., description="Number of events in window triggering the rule")
    triggering_event_ids: List[str] = Field(default_factory=list, description="IDs of events participating in pattern")
    supporting_event_ids: List[str] = Field(default_factory=list, description="Alias for triggering_event_ids")
    latest_event_id: str = Field(..., description="Latest event ID in the triggering window")
    alert_id: Optional[str] = Field(None, description="Linked alert ID (newly created or deduplicated)")
    created_alert: bool = Field(False, description="True if a new alert was stored; False if deduplicated")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Detection timestamp")


class AnomalyDetectResponse(BaseModel):
    scanned_agents: List[str] = Field(default_factory=list, description="List of scanned agent IDs")
    total_events_analyzed: int = Field(0, description="Total events inspected in the stream")
    rules_evaluated: List[str] = Field(
        default_factory=lambda: [
            "Rule A: Repeated High-Risk Activity (>= 3 high/crit in 5m)",
            "Rule B: Repeated Policy Violations (>= 3 block/quarantine in 5m)",
            "Rule C: Action Burst / Behavioral Spike (>= 10 actions in 1m)",
        ],
        description="Deterministic rules evaluated",
    )
    anomalies_detected: int = Field(0, description="Total anomalous patterns detected")
    alerts_created: int = Field(0, description="Count of new alerts stored")
    new_alerts_created: int = Field(0, description="Alias for alerts_created")
    alerts_deduplicated: int = Field(0, description="Count of duplicate anomalies matching existing alerts")
    relevant_event_ids: List[str] = Field(default_factory=list, description="Unique IDs of all events participating in anomalies")
    anomalies: List[DetectedAnomaly] = Field(default_factory=list, description="List of detected anomalies")
