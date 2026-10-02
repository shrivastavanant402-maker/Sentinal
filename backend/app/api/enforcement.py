import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from backend.app.db.repository import get_repository
from backend.app.pdp.engine import get_pdp
from backend.app.schemas.decision import ActionRequest, DecisionResponse, DecisionStatus
from backend.app.schemas.event import EventCreate

logger = logging.getLogger("aegismesh.api.enforcement")

router = APIRouter(prefix="/enforce", tags=["Enforcement"])


async def execute_enforcement(request: ActionRequest) -> DecisionResponse:
    """
    Core Policy Enforcement Point evaluation logic.
    Looks up agent, evaluates through PDP, records tamper-proof ledger event,
    and returns strongly typed DecisionResponse.
    """
    repo = get_repository()
    pdp = get_pdp()

    # ── 1. Look up the agent (do NOT auto-register) ──────────────────────────
    agent = await repo.get_agent(request.agent_id)

    # ── 2. Evaluate through PDP ──────────────────────────────────────────────
    decision: DecisionResponse = await pdp.evaluate(request, agent=agent)

    # ── 3. Record enforcement event in the ledger ────────────────────────────
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    decision_dict = {
        "status": decision.decision.value,
        "allowed": decision.allowed,
        "reason": decision.reason.value if hasattr(decision.reason, "value") else str(decision.reason),
        "risk_level": decision.risk_level.value,
        "details": decision.details,
    }

    ledger_event = EventCreate(
        id=event_id,
        agent_id=request.agent_id,
        session_id=request.session_id,
        event_type="enforcement",
        action=request.action,
        payload={
            "requested_payload": request.payload,
            "mission_id": request.mission_id,
            "provenance": request.provenance,
        },
        decision=decision_dict,
        timestamp=now,
    )

    try:
        stored = await repo.store_event(ledger_event)
        decision.event_id = stored.id
    except Exception as exc:
        logger.warning(
            "Could not persist ledger event for unregistered or invalid agent '%s': %s",
            request.agent_id,
            exc,
        )
        decision.event_id = None

    logger.info(
        "Enforcement: agent=%s action=%s decision=%s event_id=%s",
        request.agent_id,
        request.action,
        decision.decision.value,
        decision.event_id,
    )

    return decision


@router.post("", response_model=DecisionResponse)
async def enforce_action(request: ActionRequest) -> DecisionResponse:
    """
    Policy Enforcement Point — synchronous security gate.

    Agents MUST call this endpoint BEFORE executing any action.

    The endpoint:
      1. Looks up the agent record (unknown agent → BLOCK).
      2. Delegates to the PDP engine for a security decision.
      3. Records the enforcement decision as a tamper-proof ledger event.
      4. Returns the DecisionResponse.

    This endpoint does NOT execute the requested action.
    The caller (agent) is responsible for honouring the decision.

    HTTP 200 is always returned for a valid evaluation.
    The caller must inspect ``allowed`` / ``decision`` in the response body.
    HTTP 422 is returned only for a malformed/unparseable request body.
    """
    return await execute_enforcement(request)
