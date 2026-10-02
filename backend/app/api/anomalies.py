from typing import Optional
from fastapi import APIRouter, status

from backend.app.anomalies.detector import get_anomaly_detector
from backend.app.schemas.anomaly import AnomalyDetectRequest, AnomalyDetectResponse

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.post(
    "/detect",
    response_model=AnomalyDetectResponse,
    status_code=status.HTTP_200_OK,
)
async def detect_anomalies(
    request: Optional[AnomalyDetectRequest] = None,
) -> AnomalyDetectResponse:
    """
    Scans the runtime event stream for suspicious behavioral anomaly patterns:
      - Rule A: Repeated High-Risk Actions (>= 3 high/critical within 5m) -> REPEATED_HIGH_RISK_ACTIVITY
      - Rule B: Repeated Policy Violations (>= 3 block/quarantine within 5m) -> REPEATED_POLICY_VIOLATIONS
      - Rule C: Action Burst / Behavioral Spike (>= 10 actions within 1m) -> ACTION_BURST_ANOMALY

    Creates dedicated SOC alerts when anomalies are identified.
    Deduplicates deterministically: repeated calls with identical events do NOT duplicate alerts.
    Does not modify agent state, PEP decisions, or trust scores.
    """
    detector = get_anomaly_detector()
    req = request or AnomalyDetectRequest()
    return await detector.detect_anomalies(
        agent_id=req.agent_id,
        window_seconds=req.window_seconds or 300,
    )


@router.get(
    "/detect",
    response_model=AnomalyDetectResponse,
    status_code=status.HTTP_200_OK,
)
async def detect_anomalies_get(
    agent_id: Optional[str] = None,
    window_seconds: int = 300,
) -> AnomalyDetectResponse:
    """Convenience GET endpoint for triggering on-demand anomaly detection scan."""
    detector = get_anomaly_detector()
    return await detector.detect_anomalies(
        agent_id=agent_id,
        window_seconds=window_seconds,
    )
