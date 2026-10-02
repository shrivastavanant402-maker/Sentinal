"""
Trust & Quarantine REST API — AegisMesh Phase 2

Endpoints:
    GET  /trust/{agent_id}          — get current trust score for an agent
    GET  /trust                     — list all trust scores
    POST /quarantine/{agent_id}     — manually quarantine an agent
    POST /quarantine/{agent_id}/release — release a quarantined agent
    GET  /quarantine                — list currently quarantined agents
    GET  /provenance/taint-hits     — list all taint sink hits
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.enforcement.quarantine import get_quarantine_controller
from backend.app.provenance.tracker import get_provenance_tracker
from backend.app.trust.engine import get_trust_engine

logger = logging.getLogger("aegismesh.api.trust")

router = APIRouter(tags=["Trust & Quarantine"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QuarantineRequest(BaseModel):
    reason: str = "Manual admin quarantine"


class ReleaseRequest(BaseModel):
    reason: str = "Manual admin release"


# ---------------------------------------------------------------------------
# Trust endpoints
# ---------------------------------------------------------------------------

@router.get("/trust/{agent_id}", summary="Get trust score for an agent")
async def get_agent_trust(agent_id: str) -> Dict[str, Any]:
    """Return the current multi-dimensional trust score for an agent."""
    engine = get_trust_engine()
    score = await engine.get_score(agent_id)
    return score.to_dict()


@router.get("/trust", summary="List all agent trust scores")
async def list_trust_scores() -> List[Dict[str, Any]]:
    """Return trust scores for all agents tracked by the trust engine."""
    engine = get_trust_engine()
    scores = await engine.all_scores()
    return [s.to_dict() for s in scores.values()]


# ---------------------------------------------------------------------------
# Quarantine endpoints
# ---------------------------------------------------------------------------

@router.post("/quarantine/{agent_id}", summary="Manually quarantine an agent")
async def quarantine_agent(agent_id: str, body: QuarantineRequest) -> Dict[str, Any]:
    """
    Immediately quarantine an agent. Records a ledger event.
    Idempotent — safe to call even if already quarantined.
    """
    qc = get_quarantine_controller()
    result = await qc.quarantine_agent(
        agent_id=agent_id,
        reason=body.reason,
        trigger="manual",
    )
    return result.to_dict()


@router.post("/quarantine/{agent_id}/release", summary="Release a quarantined agent")
async def release_agent(agent_id: str, body: ReleaseRequest) -> Dict[str, Any]:
    """
    Release an agent from quarantine and restore ACTIVE status.
    Records a ledger event.
    """
    qc = get_quarantine_controller()
    result = await qc.release_agent(agent_id=agent_id, reason=body.reason)
    if not result.quarantined and "error" in result.details:
        raise HTTPException(status_code=404, detail=result.reason)
    return result.to_dict()


@router.get("/quarantine", summary="List quarantined agents")
async def list_quarantined() -> Dict[str, Any]:
    """Return the list of currently quarantined agent IDs."""
    qc = get_quarantine_controller()
    quarantined = await qc.list_quarantined()
    return {"quarantined": quarantined, "count": len(quarantined)}


# ---------------------------------------------------------------------------
# Provenance endpoints
# ---------------------------------------------------------------------------

@router.get("/provenance/taint-hits", summary="List all taint sink hit events")
async def list_taint_hits() -> List[Dict[str, Any]]:
    """Return all recorded taint hit events (sensitive data reaching forbidden sinks)."""
    tracker = get_provenance_tracker()
    hits = await tracker.list_taint_hits()
    return [h.to_dict() for h in hits]


@router.get("/provenance/taint/{agent_id}", summary="Get taint status for an agent")
async def get_agent_taint(agent_id: str) -> Dict[str, Any]:
    """Return the current taint label for an agent."""
    tracker = get_provenance_tracker()
    label = await tracker.get_agent_taint(agent_id)
    return {
        "agent_id": agent_id,
        "taint_label": label.value,
        "is_clean": label.value == "CLEAN",
    }
