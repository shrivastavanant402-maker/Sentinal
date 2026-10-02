#!/usr/bin/env python3
"""
scripts/verify_step7.py -- Step 7 End-to-End Chain Integrity Verifier

Verifies the complete Step 7 security chain:
  1. Ed25519 key generation
  2. Agent registration with public key
  3. Enforcement with valid signed request -> accepted at PDP identity check
  4. Enforcement with replay (same nonce) -> BLOCK
  5. Enforcement with tampered payload -> BLOCK
  6. Enforcement with unsigned request (agent has key) -> BLOCK (INVALID_IDENTITY)
  7. Ledger integrity still valid after all enforcement events

Runs entirely in-process via httpx.ASGITransport (no external server needed).
Exit 0 = all checks passed. Exit 1 = at least one check failed.
"""

import asyncio
import sys
import time
import uuid
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx

from backend.app.identity.crypto import (
    create_canonical_message,
    generate_ed25519_keypair,
    sign_canonical_request,
)
from backend.app.identity.replay import ReplayCache
from backend.app.identity.verifier import IdentityVerifier, set_identity_verifier
from backend.app.pdp.engine import PolicyDecisionPoint, set_pdp

PASS = "[PASS]"
FAIL = "[FAIL]"

_checks: list[tuple[str, bool]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    symbol = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  {symbol} {label}{suffix}")
    _checks.append((label, condition))


async def run_verifier() -> int:
    print()
    print("=" * 56)
    print("  AegisMesh -- Step 7 E2E Chain Integrity Verifier")
    print("=" * 56)
    print()

    # Fresh isolated replay cache for this run
    fresh_cache = ReplayCache(ttl_seconds=300)
    verifier = IdentityVerifier(
        replay_cache=fresh_cache,
        clock_skew_seconds=300.0,
        strict_signatures=False,
    )
    set_identity_verifier(verifier)

    pdp = PolicyDecisionPoint(identity_verifier=verifier)
    set_pdp(pdp)

    from backend.app.main import app as asgi_app
    transport = httpx.ASGITransport(app=asgi_app)
    base_url = "http://testserver"

    # ---- Step 7.1: Key Generation -----------------------------------------
    print("-- Step 7.1: Ed25519 Key Generation --")
    priv, pub_hex = generate_ed25519_keypair()
    check(
        "generate_ed25519_keypair() returns 32-byte public key",
        len(pub_hex) == 64,
        f"len={len(pub_hex) // 2} bytes",
    )

    agent_id = f"verify-step7-{uuid.uuid4().hex[:8]}"

    # ---- Step 7.2: Registration with Public Key ---------------------------
    print()
    print("-- Step 7.2: Agent Registration with Public Key --")
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        reg_resp = await client.post(
            "/agents/register",
            json={
                "id": agent_id,
                "name": "Step7 Verifier Agent",
                "role": "verifier",
                "capabilities": ["web.search", "file.read"],
                "metadata": {},
                "public_key": pub_hex,
            },
        )
        check(
            "Agent registration returns 200 or 201",
            reg_resp.status_code in (200, 201),
            f"status={reg_resp.status_code}",
        )
        reg_data = reg_resp.json()
        check(
            "Registered agent has correct public_key",
            reg_data.get("public_key") == pub_hex,
        )

    # ---- Step 7.3: Valid Signed Request ------------------------------------
    print()
    print("-- Step 7.3: Signed Request Passes Identity Check --")
    ts = time.time()
    nonce = str(uuid.uuid4())
    payload = {"query": "safe search"}
    msg = create_canonical_message(agent_id, "web.search", payload, None, ts, nonce)
    sig = sign_canonical_request(priv, msg)

    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        enforce_resp = await client.post(
            "/enforce",
            json={
                "agent_id": agent_id,
                "action": "web.search",
                "payload": payload,
                "signature": sig,
                "timestamp": ts,
                "nonce": nonce,
            },
        )
        check("Enforce returns HTTP 200", enforce_resp.status_code == 200,
              f"status={enforce_resp.status_code}")
        data = enforce_resp.json()
        check(
            "Decision is NOT INVALID_IDENTITY",
            data.get("reason") != "INVALID_IDENTITY",
            f"reason={data.get('reason')} decision={data.get('decision')}",
        )

    # ---- Step 7.4: Replay Attack -------------------------------------------
    print()
    print("-- Step 7.4: Replay Attack is Blocked --")
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        replay_resp = await client.post(
            "/enforce",
            json={
                "agent_id": agent_id,
                "action": "web.search",
                "payload": payload,
                "signature": sig,
                "timestamp": ts,
                "nonce": nonce,  # same nonce!
            },
        )
        check("Replay returns HTTP 200", replay_resp.status_code == 200)
        rdata = replay_resp.json()
        check("Replay decision is BLOCK", rdata.get("decision") == "BLOCK",
              f"decision={rdata.get('decision')}")
        check("Replay reason is INVALID_IDENTITY",
              rdata.get("reason") == "INVALID_IDENTITY",
              f"reason={rdata.get('reason')}")

    # ---- Step 7.5: Tampered Payload ----------------------------------------
    print()
    print("-- Step 7.5: Tampered Payload is Blocked --")
    ts2 = time.time()
    nonce2 = str(uuid.uuid4())
    orig_payload = {"query": "safe search"}
    tampered_payload = {"query": "DROP TABLE agents; --"}
    msg2 = create_canonical_message(agent_id, "web.search", orig_payload, None, ts2, nonce2)
    sig2 = sign_canonical_request(priv, msg2)

    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        tamper_resp = await client.post(
            "/enforce",
            json={
                "agent_id": agent_id,
                "action": "web.search",
                "payload": tampered_payload,  # different from what was signed
                "signature": sig2,
                "timestamp": ts2,
                "nonce": nonce2,
            },
        )
        check("Tampered request returns HTTP 200", tamper_resp.status_code == 200)
        tdata = tamper_resp.json()
        check("Tampered payload decision is BLOCK",
              tdata.get("decision") == "BLOCK",
              f"decision={tdata.get('decision')}")
        check("Tampered payload reason is INVALID_IDENTITY",
              tdata.get("reason") == "INVALID_IDENTITY",
              f"reason={tdata.get('reason')}")

    # ---- Step 7.6: Unsigned Request from Keyed Agent -----------------------
    print()
    print("-- Step 7.6: Unsigned Request from Keyed Agent Blocked --")
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        unsigned_resp = await client.post(
            "/enforce",
            json={
                "agent_id": agent_id,
                "action": "file.read",
                "payload": {"path": "/etc/passwd"},
            },
        )
        check("Unsigned request returns HTTP 200", unsigned_resp.status_code == 200)
        udata = unsigned_resp.json()
        check("Unsigned from keyed agent is BLOCK",
              udata.get("decision") == "BLOCK",
              f"decision={udata.get('decision')}")
        check("Unsigned reason is INVALID_IDENTITY",
              udata.get("reason") == "INVALID_IDENTITY",
              f"reason={udata.get('reason')}")

    # ---- Step 7.7: Ledger Integrity ----------------------------------------
    print()
    print("-- Step 7.7: Ledger Integrity After All Events --")
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        ledger_resp = await client.get("/ledger/verify")
        check("Ledger verify returns HTTP 200",
              ledger_resp.status_code == 200,
              f"status={ledger_resp.status_code}")
        ldata = ledger_resp.json()
        chain_ok = ldata.get("ok") is True or ldata.get("chain_valid") is True
        check("Ledger integrity is valid",
              chain_ok,
              f"ok={ldata.get('ok')} chain_valid={ldata.get('chain_valid')} checked={ldata.get('checked')}")  

    # ---- Summary -----------------------------------------------------------
    passed = sum(1 for _, ok in _checks if ok)
    total = len(_checks)
    failed = total - passed

    print()
    print("=" * 56)
    if failed:
        print(f"  Result: {passed}/{total} checks passed  [{failed} FAILED]")
    else:
        print(f"  Result: {passed}/{total} checks passed  [ALL PASSED]")
    print("=" * 56)
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_verifier())
    sys.exit(exit_code)
