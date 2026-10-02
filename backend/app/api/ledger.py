from fastapi import APIRouter
from backend.app.db.repository import get_repository
from backend.app.ledger.verifier import verify_ledger_chain

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get("/verify")
async def verify_ledger():
    """
    Verifies the integrity of the cryptographic hash-chain across all recorded events.
    Returns chain validity, event count, and any broken links or corrupted payloads.
    """
    repo = get_repository()
    # Retrieve all events for chain verification
    events = await repo.list_events(limit=10000, offset=0)
    events_dict = [ev.model_dump() for ev in events]
    report = verify_ledger_chain(events_dict)
    return report
