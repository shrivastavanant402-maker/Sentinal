from datetime import datetime, timezone
import pytest
from backend.app.ledger.hasher import calculate_content_hash, calculate_event_hash
from backend.app.ledger.verifier import verify_ledger_chain


def test_same_event_same_decision_same_hash():
    now = datetime.now(timezone.utc)
    decision = {"allowed": True, "status": "ALLOW", "reason": "ALLOWED_BY_POLICY"}

    hash1 = calculate_content_hash(
        event_id="ev-1",
        agent_id="researcher-01",
        event_type="tool_call_request",
        action="web.search",
        payload={"query": "security"},
        timestamp=now,
        session_id="sess-1",
        decision=decision
    )

    hash2 = calculate_content_hash(
        event_id="ev-1",
        agent_id="researcher-01",
        event_type="tool_call_request",
        action="web.search",
        payload={"query": "security"},
        timestamp=now,
        session_id="sess-1",
        decision=decision
    )

    assert hash1 == hash2


def test_same_event_different_decision_different_hash():
    now = datetime.now(timezone.utc)
    decision_allow = {"allowed": True, "status": "ALLOW", "reason": "ALLOWED_BY_POLICY"}
    decision_block = {"allowed": False, "status": "BLOCK", "reason": "CONTRACT_VIOLATION"}

    hash_allow = calculate_content_hash(
        event_id="ev-1",
        agent_id="researcher-01",
        event_type="tool_call_request",
        action="web.search",
        payload={"query": "security"},
        timestamp=now,
        session_id="sess-1",
        decision=decision_allow
    )

    hash_block = calculate_content_hash(
        event_id="ev-1",
        agent_id="researcher-01",
        event_type="tool_call_request",
        action="web.search",
        payload={"query": "security"},
        timestamp=now,
        session_id="sess-1",
        decision=decision_block
    )

    assert hash_allow != hash_block


def test_tampering_decision_fails_ledger_verification():
    now = datetime.now(timezone.utc)
    initial_decision = {"allowed": True, "status": "ALLOW", "reason": "ALLOWED_BY_POLICY"}

    content_hash = calculate_content_hash(
        event_id="ev-1",
        agent_id="researcher-01",
        event_type="tool_call_request",
        action="web.search",
        payload={"query": "security"},
        timestamp=now,
        session_id="sess-1",
        decision=initial_decision
    )

    prev_hash = "0" * 64
    event_hash = calculate_event_hash(
        seq=1,
        content_hash=content_hash,
        previous_hash=prev_hash,
        timestamp=now
    )

    valid_event = {
        "id": "ev-1",
        "seq": 1,
        "agent_id": "researcher-01",
        "session_id": "sess-1",
        "event_type": "tool_call_request",
        "action": "web.search",
        "payload": {"query": "security"},
        "timestamp": now.isoformat(),
        "decision": initial_decision,
        "content_hash": content_hash,
        "previous_hash": prev_hash,
        "event_hash": event_hash
    }

    # Verify untampered event passes
    report_valid = verify_ledger_chain([valid_event])
    assert report_valid["ok"] is True
    assert report_valid["chain_valid"] is True
    assert len(report_valid["errors"]) == 0

    # Tamper with the decision (e.g. attacker changes ALLOW to BLOCK or alters reason)
    tampered_event = dict(valid_event)
    tampered_event["decision"] = {"allowed": False, "status": "BLOCK", "reason": "TAMPERED"}

    # Verification must catch the tampering because content_hash no longer matches the decision!
    report_tampered = verify_ledger_chain([tampered_event])
    assert report_tampered["ok"] is False
    assert report_tampered["chain_valid"] is False
    assert len(report_tampered["errors"]) > 0
    assert any("Content hash mismatch" in err for err in report_tampered["errors"])
