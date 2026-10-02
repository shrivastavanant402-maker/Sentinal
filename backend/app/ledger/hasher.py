import hashlib
import json
from datetime import datetime
from typing import Any, Dict


def to_canonical_json(data: Any) -> str:
    """
    Serializes a dictionary or value into canonical JSON:
    - Sorted keys
    - No unnecessary whitespace
    - ISO formatted datetimes
    """
    def default_serializer(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=default_serializer,
        ensure_ascii=False
    )


def compute_sha256(canonical_str: str) -> str:
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def calculate_content_hash(
    event_id: str,
    agent_id: str,
    event_type: str,
    action: str,
    payload: Dict[str, Any],
    timestamp: datetime,
    session_id: str | None = None
) -> str:
    """
    Calculates content_hash of the event prior to ledger sequencing and chaining.
    """
    content_dict = {
        "id": event_id,
        "agent_id": agent_id,
        "event_type": event_type,
        "action": action,
        "payload": payload,
        "session_id": session_id or "",
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
    }
    return compute_sha256(to_canonical_json(content_dict))


def calculate_event_hash(
    seq: int,
    content_hash: str,
    previous_hash: str,
    timestamp: datetime
) -> str:
    """
    Calculates final tamper-proof event_hash incorporating content_hash and previous_hash.
    """
    chain_dict = {
        "seq": seq,
        "content_hash": content_hash,
        "previous_hash": previous_hash,
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
    }
    return compute_sha256(to_canonical_json(chain_dict))
