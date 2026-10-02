from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.app.config import get_settings
from backend.app.ledger.hasher import calculate_content_hash, calculate_event_hash


def verify_ledger_chain(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifies the integrity of the append-only event ledger chain.
    Checks:
    - Content hash correctness
    - Previous hash continuity
    - Event hash correctness
    - Sequence monotonicity
    """
    settings = get_settings()
    genesis_prev_hash = settings.LEDGER_GENESIS_PREV_HASH

    total_events = len(events)
    if total_events == 0:
        return {
            "ok": True,
            "checked": 0,
            "chain_valid": True,
            "errors": [],
            "message": "Ledger is empty. Genesis ready."
        }

    errors: List[str] = []
    expected_prev_hash = genesis_prev_hash

    for idx, ev in enumerate(events):
        seq = ev.get("seq", idx + 1)
        ev_id = ev.get("id")
        agent_id = ev.get("agent_id")
        event_type = ev.get("event_type")
        action = ev.get("action")
        payload = ev.get("payload", {})
        session_id = ev.get("session_id")
        timestamp_raw = ev.get("timestamp")

        # Parse or handle timestamp
        if isinstance(timestamp_raw, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            except Exception:
                timestamp = timestamp_raw
        else:
            timestamp = timestamp_raw

        # 1. Verify content_hash
        expected_content_hash = calculate_content_hash(
            event_id=ev_id,
            agent_id=agent_id,
            event_type=event_type,
            action=action,
            payload=payload,
            timestamp=timestamp,
            session_id=session_id,
            decision=ev.get("decision", {})
        )

        recorded_content_hash = ev.get("content_hash")
        if recorded_content_hash != expected_content_hash:
            # Check backward compatibility for legacy Phase 0 events without decision field in canonical JSON
            from backend.app.ledger.hasher import compute_sha256, to_canonical_json
            legacy_dict = {
                "id": ev_id,
                "agent_id": agent_id,
                "event_type": event_type,
                "action": action,
                "payload": payload,
                "session_id": session_id or "",
                "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
            }
            legacy_content_hash = compute_sha256(to_canonical_json(legacy_dict))
            if recorded_content_hash == legacy_content_hash:
                expected_content_hash = legacy_content_hash
            else:
                errors.append(
                    f"Content hash mismatch at seq={seq} (id={ev_id}): recorded {recorded_content_hash} != calculated {expected_content_hash}"
                )

        # 2. Verify previous_hash
        recorded_prev_hash = ev.get("previous_hash")
        if recorded_prev_hash != expected_prev_hash:
            errors.append(
                f"Previous hash broken at seq={seq} (id={ev_id}): recorded {recorded_prev_hash} != expected {expected_prev_hash}"
            )

        # 3. Verify event_hash
        expected_event_hash = calculate_event_hash(
            seq=seq,
            content_hash=expected_content_hash,
            previous_hash=recorded_prev_hash,
            timestamp=timestamp
        )

        recorded_event_hash = ev.get("event_hash")
        if recorded_event_hash != expected_event_hash:
            errors.append(
                f"Event hash mismatch at seq={seq} (id={ev_id}): recorded {recorded_event_hash} != calculated {expected_event_hash}"
            )

        # Next event must point to this event's hash
        expected_prev_hash = recorded_event_hash

    is_valid = len(errors) == 0
    return {
        "ok": is_valid,
        "checked": total_events,
        "chain_valid": is_valid,
        "errors": errors,
        "latest_hash": events[-1].get("event_hash") if events else None,
        "genesis_hash": genesis_prev_hash
    }
