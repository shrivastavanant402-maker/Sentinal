from datetime import datetime, timezone
from backend.app.ledger.hasher import (
    to_canonical_json,
    compute_sha256,
    calculate_content_hash,
    calculate_event_hash
)


def test_canonical_json_ordering():
    dict1 = {"b": 2, "a": 1, "nested": {"z": 100, "y": 50}}
    dict2 = {"a": 1, "nested": {"y": 50, "z": 100}, "b": 2}
    assert to_canonical_json(dict1) == to_canonical_json(dict2)
    assert compute_sha256(to_canonical_json(dict1)) == compute_sha256(to_canonical_json(dict2))


def test_content_and_event_hash():
    now = datetime.now(timezone.utc)
    ch = calculate_content_hash(
        event_id="ev-123",
        agent_id="researcher-01",
        event_type="tool_call_request",
        action="web.search",
        payload={"query": "test query"},
        timestamp=now
    )
    assert isinstance(ch, str)
    assert len(ch) == 64

    eh = calculate_event_hash(
        seq=1,
        content_hash=ch,
        previous_hash="0" * 64,
        timestamp=now
    )
    assert isinstance(eh, str)
    assert len(eh) == 64
    assert eh != ch
