import json
import logging
from typing import Any, Dict, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger("aegismesh.identity.crypto")


def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, str]:
    """
    Generates a new Ed25519 private key and returns (private_key, public_key_hex).
    The private key stays strictly in memory with the agent.
    Only public_key_hex (32 bytes / 64 hex chars) is transmitted or stored.
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_hex = public_key.public_bytes_raw().hex()
    return private_key, public_key_hex


def create_canonical_message(
    agent_id: str,
    action: str,
    payload: Dict[str, Any],
    mission_id: Optional[str] = None,
    timestamp: float = 0.0,
    nonce: str = "",
) -> bytes:
    """
    Constructs a deterministic, canonical JSON representation of the security-relevant
    request parameters.

    Fields signed:
      - action
      - agent_id
      - mission_id (normalized to empty string if None)
      - nonce
      - payload (keys sorted alphabetically)
      - timestamp (normalized to 4 decimal places)
    """
    canonical_dict = {
        "action": str(action),
        "agent_id": str(agent_id),
        "mission_id": str(mission_id) if mission_id else "",
        "nonce": str(nonce),
        "payload": payload or {},
        "timestamp": round(float(timestamp), 4),
    }
    canonical_json = json.dumps(
        canonical_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return canonical_json.encode("utf-8")


def sign_canonical_request(
    private_key: ed25519.Ed25519PrivateKey,
    message: bytes,
) -> str:
    """
    Signs the canonical request bytes using Ed25519.
    Returns the signature formatted as a 128-character hexadecimal string (64 bytes).
    """
    signature = private_key.sign(message)
    return signature.hex()


def verify_ed25519_signature(
    public_key_hex: str,
    message: bytes,
    signature_hex: str,
) -> bool:
    """
    Verifies an Ed25519 signature over a canonical message bytes against a public key hex.
    Returns True if valid, False otherwise. Fails closed on any error.
    """
    if not public_key_hex or not signature_hex:
        return False

    try:
        public_bytes = bytes.fromhex(public_key_hex)
        if len(public_bytes) != 32:
            logger.warning("Invalid Ed25519 public key byte length: %d (expected 32)", len(public_bytes))
            return False

        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)

        sig_bytes = bytes.fromhex(signature_hex)
        if len(sig_bytes) != 64:
            logger.warning("Invalid Ed25519 signature byte length: %d (expected 64)", len(sig_bytes))
            return False

        public_key.verify(sig_bytes, message)
        return True
    except InvalidSignature:
        logger.warning("Ed25519 signature verification failed")
        return False
    except Exception as exc:
        logger.warning("Error verifying Ed25519 signature: %s", exc)
        return False
