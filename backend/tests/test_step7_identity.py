"""
test_step7_identity.py — Step 7: Agent Identity & Security Hardening

Security Invariants Verified:
  1.  Registered agent with valid signature → ALLOW (happy path)
  2.  Registered agent with no key → ALLOW without signature required (non-strict mode)
  3.  Agent registered with public key, submits no signature → BLOCK (INVALID_IDENTITY)
  4.  Agent registered with public key, submits wrong/tampered signature → BLOCK
  5.  Unregistered agent → BLOCK (existing Step 1 fast-path still in place)
  6.  Replay protection: reusing nonce on second request → BLOCK
  7.  Expired timestamp → BLOCK
  8.  Malformed signature (bad hex, wrong length) → BLOCK
  9.  Strict mode: agent without public key → BLOCK
  10. Identity failure NEVER converts an existing BLOCK into ALLOW
  11. Missing nonce on signed request → BLOCK
  12. Missing timestamp on signed request → BLOCK
  13. Valid signature but mismatched payload (tampered body) → BLOCK
  14. generate_ed25519_keypair() produces valid 32-byte key pairs
  15. create_canonical_message() is deterministic (same inputs → same bytes)
  16. ReplayCache records and rejects a reused nonce
  17. ReplayCache allows a different nonce from the same agent
  18. AegisMeshClient._attach_identity_proof() auto-signs when private key present
  19. AegisMeshClient._attach_identity_proof() no-op when no private key
  20. PDP strict-mode integration: no public key → BLOCK via verifier
"""

import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from backend.app.identity.crypto import (
    create_canonical_message,
    generate_ed25519_keypair,
    sign_canonical_request,
    verify_ed25519_signature,
)
from backend.app.identity.replay import ReplayCache
from backend.app.identity.schemas import IdentityVerificationStatus
from backend.app.identity.verifier import IdentityVerifier
from backend.app.schemas.agent import AgentResponse, AgentStatus
from backend.app.schemas.decision import (
    ActionRequest,
    DecisionReason,
    DecisionStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(
    agent_id: str = "agent-id-test",
    public_key: str | None = None,
    status: AgentStatus = AgentStatus.ACTIVE,
    trust_score: float = 100.0,
) -> AgentResponse:
    return AgentResponse(
        id=agent_id,
        name="Test Agent",
        role="tester",
        status=status,
        trust_score=trust_score,
        public_key=public_key,
        capabilities=[],
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_signed_request(
    private_key,
    agent_id: str = "agent-id-test",
    action: str = "web.search",
    payload: dict | None = None,
    mission_id: str | None = None,
    now: float | None = None,
    nonce: str | None = None,
) -> ActionRequest:
    ts = now if now is not None else time.time()
    n = nonce or str(uuid.uuid4())
    p = payload or {}
    msg = create_canonical_message(
        agent_id=agent_id,
        action=action,
        payload=p,
        mission_id=mission_id,
        timestamp=ts,
        nonce=n,
    )
    sig = sign_canonical_request(private_key, msg)
    return ActionRequest(
        agent_id=agent_id,
        action=action,
        payload=p,
        mission_id=mission_id,
        signature=sig,
        timestamp=ts,
        nonce=n,
    )


def _make_fresh_verifier(strict: bool = False) -> IdentityVerifier:
    """Each test gets an isolated replay cache."""
    return IdentityVerifier(
        replay_cache=ReplayCache(ttl_seconds=300),
        clock_skew_seconds=300.0,
        strict_signatures=strict,
    )


# ===========================================================================
# 1–2: Crypto primitives
# ===========================================================================

class TestCryptoPrimitives:
    """Tests 14–15: Ed25519 key generation and canonical message determinism."""

    def test_14_generate_keypair_produces_valid_32byte_pubkey(self):
        priv, pub_hex = generate_ed25519_keypair()
        assert len(pub_hex) == 64, "Public key hex must be 64 chars (32 bytes)"
        assert bytes.fromhex(pub_hex)  # parseable hex

    def test_15_canonical_message_is_deterministic(self):
        args = dict(
            agent_id="agent-x",
            action="file.read",
            payload={"path": "/etc/passwd"},
            mission_id="m-1",
            timestamp=1700000000.1234,
            nonce="test-nonce-abc",
        )
        m1 = create_canonical_message(**args)
        m2 = create_canonical_message(**args)
        assert m1 == m2

    def test_canonical_message_payload_key_order_independent(self):
        """Sorted keys mean {b: 2, a: 1} == {a: 1, b: 2} in canonical form."""
        base = dict(
            agent_id="a", action="x", mission_id=None,
            timestamp=1000.0, nonce="n",
        )
        m1 = create_canonical_message(**base, payload={"b": 2, "a": 1})
        m2 = create_canonical_message(**base, payload={"a": 1, "b": 2})
        assert m1 == m2

    def test_verify_ed25519_roundtrip(self):
        priv, pub_hex = generate_ed25519_keypair()
        msg = b"hello aegismesh"
        sig_hex = priv.sign(msg).hex()
        assert verify_ed25519_signature(pub_hex, msg, sig_hex) is True

    def test_verify_ed25519_wrong_key_returns_false(self):
        priv1, _ = generate_ed25519_keypair()
        _, pub_hex2 = generate_ed25519_keypair()
        sig_hex = priv1.sign(b"msg").hex()
        assert verify_ed25519_signature(pub_hex2, b"msg", sig_hex) is False

    def test_verify_ed25519_tampered_message_returns_false(self):
        priv, pub_hex = generate_ed25519_keypair()
        sig_hex = priv.sign(b"original").hex()
        assert verify_ed25519_signature(pub_hex, b"tampered!", sig_hex) is False

    def test_verify_ed25519_empty_key_returns_false(self):
        assert verify_ed25519_signature("", b"msg", "aabb") is False

    def test_verify_ed25519_bad_hex_returns_false(self):
        priv, pub_hex = generate_ed25519_keypair()
        assert verify_ed25519_signature(pub_hex, b"msg", "not_hex_!!!") is False


# ===========================================================================
# 3: Replay Cache
# ===========================================================================

class TestReplayCache:
    """Tests 16–17: Nonce recording and rejection."""

    @pytest.mark.asyncio
    async def test_16_cache_rejects_replayed_nonce(self):
        cache = ReplayCache(ttl_seconds=300)
        nonce = str(uuid.uuid4())
        now = time.time()
        assert await cache.check_and_record(nonce, now, now) is True
        assert await cache.check_and_record(nonce, now, now) is False

    @pytest.mark.asyncio
    async def test_17_cache_allows_different_nonce(self):
        cache = ReplayCache(ttl_seconds=300)
        now = time.time()
        assert await cache.check_and_record("nonce-a", now, now) is True
        assert await cache.check_and_record("nonce-b", now, now) is True

    @pytest.mark.asyncio
    async def test_cache_rejects_expired_timestamp(self):
        cache = ReplayCache(ttl_seconds=60)
        old_ts = time.time() - 120  # 2 min ago
        result = await cache.check_and_record("old-nonce", old_ts, time.time())
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_clear_resets_state(self):
        cache = ReplayCache(ttl_seconds=300)
        now = time.time()
        await cache.check_and_record("n1", now, now)
        await cache.clear()
        assert await cache.check_and_record("n1", now, now) is True


# ===========================================================================
# 4: IdentityVerifier unit tests
# ===========================================================================

class TestIdentityVerifier:
    """Tests 1–13: IdentityVerifier security boundary invariants."""

    @pytest.mark.asyncio
    async def test_01_valid_signed_request_is_verified(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        request = _make_signed_request(priv)
        result = await verifier.verify(request, agent)
        assert result.is_valid is True
        assert result.status == IdentityVerificationStatus.VALID

    @pytest.mark.asyncio
    async def test_02_unsigned_request_no_pubkey_agent_passes(self):
        """Non-strict mode: agent without key, no signature → VALID."""
        agent = _make_agent(public_key=None)
        verifier = _make_fresh_verifier(strict=False)
        request = ActionRequest(agent_id="agent-id-test", action="read.file")
        result = await verifier.verify(request, agent)
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_03_agent_with_pubkey_submits_no_sig_blocked(self):
        _, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        request = ActionRequest(agent_id="agent-id-test", action="web.search")
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.INVALID_SIGNATURE

    @pytest.mark.asyncio
    async def test_04_wrong_signature_is_blocked(self):
        priv, pub_hex = generate_ed25519_keypair()
        priv2, _ = generate_ed25519_keypair()  # different key
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        # Sign with wrong key
        request = _make_signed_request(priv2)  # signed by priv2, verified against pub_hex
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.INVALID_SIGNATURE

    @pytest.mark.asyncio
    async def test_05_unknown_agent_is_blocked(self):
        verifier = _make_fresh_verifier()
        request = ActionRequest(agent_id="ghost-agent", action="read.file")
        result = await verifier.verify(request, agent=None)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.UNKNOWN_AGENT

    @pytest.mark.asyncio
    async def test_06_replay_protection_second_request_blocked(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        request = _make_signed_request(priv)
        # First request: fresh
        r1 = await verifier.verify(request, agent)
        assert r1.is_valid is True
        # Second request: same nonce → replay
        r2 = await verifier.verify(request, agent)
        assert r2.is_valid is False
        assert r2.status == IdentityVerificationStatus.REPLAYED_REQUEST

    @pytest.mark.asyncio
    async def test_07_expired_timestamp_is_blocked(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        old_ts = time.time() - 400  # 400s ago > 300s skew tolerance
        request = _make_signed_request(priv, now=old_ts)
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.EXPIRED_REQUEST

    @pytest.mark.asyncio
    async def test_08_malformed_signature_is_blocked(self):
        _, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        request = ActionRequest(
            agent_id="agent-id-test",
            action="web.search",
            signature="not_valid_hex!!!",
            timestamp=time.time(),
            nonce=str(uuid.uuid4()),
        )
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.INVALID_SIGNATURE

    @pytest.mark.asyncio
    async def test_09_strict_mode_no_pubkey_blocked(self):
        """Strict mode: agent without a public key must be blocked."""
        agent = _make_agent(public_key=None)
        verifier = _make_fresh_verifier(strict=True)
        request = ActionRequest(agent_id="agent-id-test", action="read.file")
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.MALFORMED_IDENTITY

    @pytest.mark.asyncio
    async def test_11_missing_nonce_is_blocked(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        # Signature present but no nonce
        ts = time.time()
        msg = create_canonical_message("agent-id-test", "web.search", {}, None, ts, "")
        sig = sign_canonical_request(priv, msg)
        request = ActionRequest(
            agent_id="agent-id-test",
            action="web.search",
            signature=sig,
            timestamp=ts,
            nonce=None,  # missing
        )
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.MALFORMED_IDENTITY

    @pytest.mark.asyncio
    async def test_12_missing_timestamp_is_blocked(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        request = ActionRequest(
            agent_id="agent-id-test",
            action="web.search",
            signature="a" * 128,  # dummy
            timestamp=None,  # missing
            nonce=str(uuid.uuid4()),
        )
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.MALFORMED_IDENTITY

    @pytest.mark.asyncio
    async def test_13_tampered_payload_blocked(self):
        """Sign over payload A, then submit payload B → signature fails."""
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        verifier = _make_fresh_verifier()
        # Sign genuine request
        ts = time.time()
        nonce = str(uuid.uuid4())
        msg = create_canonical_message("agent-id-test", "web.search", {"query": "safe"}, None, ts, nonce)
        sig = sign_canonical_request(priv, msg)
        # Tamper payload in the submitted request
        request = ActionRequest(
            agent_id="agent-id-test",
            action="web.search",
            payload={"query": "EVIL"},  # tampered
            signature=sig,
            timestamp=ts,
            nonce=nonce,
        )
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.INVALID_SIGNATURE

    @pytest.mark.asyncio
    async def test_signature_only_no_pubkey_blocks(self):
        """Signature provided but no matching public key on agent → BLOCK."""
        agent = _make_agent(public_key=None)
        verifier = _make_fresh_verifier()
        request = ActionRequest(
            agent_id="agent-id-test",
            action="web.search",
            signature="a" * 128,
            timestamp=time.time(),
            nonce=str(uuid.uuid4()),
        )
        result = await verifier.verify(request, agent)
        assert result.is_valid is False
        assert result.status == IdentityVerificationStatus.MALFORMED_IDENTITY


# ===========================================================================
# 5: PDP integration tests
# ===========================================================================

class TestPDPIdentityIntegration:
    """Tests 10, 20: Identity verification integrated into PDP.evaluate()."""

    def _make_pdp_with_verifier(self, strict: bool = False):
        from unittest.mock import MagicMock

        from backend.app.pdp.engine import PolicyDecisionPoint
        from backend.app.identity.verifier import IdentityVerifier

        # Isolate PDP from real storage
        mock_repo = AsyncMock()
        mock_repo.get_contract_for_agent = AsyncMock(return_value=None)

        mock_trust = AsyncMock()
        from backend.app.trust.engine import TrustScore
        _ts = TrustScore(agent_id="agent-id-test")
        mock_trust.apply_decision = AsyncMock(return_value=_ts)
        mock_trust.apply_consistency_violation = AsyncMock(return_value=_ts)

        mock_qc = AsyncMock()
        mock_qc.maybe_quarantine = AsyncMock()

        mock_provenance = AsyncMock()
        _sink_ok = AsyncMock()
        _sink_ok.is_tainted = False
        _sink_ok.record = None
        mock_provenance.check_sink = AsyncMock(return_value=_sink_ok)
        mock_provenance.mark_tainted = AsyncMock()
        from backend.app.provenance.tracker import ProvenanceTracker

        mock_drift = MagicMock()
        from backend.app.drift.detector import DriftResult, DriftSeverity
        mock_drift.evaluate = MagicMock(
            return_value=DriftResult(
                drift_score=0.0,
                severity=DriftSeverity.NONE,
                reason="no drift",
                details={},
            )
        )

        verifier = IdentityVerifier(
            replay_cache=ReplayCache(ttl_seconds=300),
            clock_skew_seconds=300.0,
            strict_signatures=strict,
        )

        pdp = PolicyDecisionPoint(
            contract_repository=mock_repo,
            identity_verifier=verifier,
            trust_evaluator=mock_trust,
            provenance_evaluator=mock_provenance,
            drift_detector=mock_drift,
            quarantine_controller=mock_qc,
        )
        return pdp

    @pytest.mark.asyncio
    async def test_pdp_valid_signed_agent_gets_allow(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        pdp = self._make_pdp_with_verifier()
        request = _make_signed_request(priv)
        decision = await pdp.evaluate(request, agent=agent)
        # Identity must PASS — reason must NOT be INVALID_IDENTITY.
        # The policy may still BLOCK for no-contract default-deny, which is expected.
        assert decision.reason != DecisionReason.INVALID_IDENTITY, (
            f"Valid signature should not produce INVALID_IDENTITY, got: {decision}"
        )

    @pytest.mark.asyncio
    async def test_10_identity_failure_cannot_convert_block_to_allow(self):
        """
        Core invariant: identity verification cannot turn a BLOCK into ALLOW.
        Even if the rest of the pipeline would approve, a bad signature must BLOCK.
        """
        _, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        pdp = self._make_pdp_with_verifier()
        # No signature on a registered+keyed agent
        request = ActionRequest(agent_id="agent-id-test", action="web.search")
        decision = await pdp.evaluate(request, agent=agent)
        assert decision.decision == DecisionStatus.BLOCK
        assert decision.allowed is False
        assert decision.reason == DecisionReason.INVALID_IDENTITY

    @pytest.mark.asyncio
    async def test_pdp_replayed_request_blocked(self):
        priv, pub_hex = generate_ed25519_keypair()
        agent = _make_agent(public_key=pub_hex)
        pdp = self._make_pdp_with_verifier()
        request = _make_signed_request(priv)
        # First evaluation: OK
        await pdp.evaluate(request, agent=agent)
        # Second evaluation with same nonce: must BLOCK
        d2 = await pdp.evaluate(request, agent=agent)
        assert d2.decision == DecisionStatus.BLOCK
        assert d2.reason == DecisionReason.INVALID_IDENTITY

    @pytest.mark.asyncio
    async def test_20_strict_mode_no_pubkey_blocked_at_pdp(self):
        """Strict mode via PDP: agent with no public key → BLOCK."""
        agent = _make_agent(public_key=None)
        pdp = self._make_pdp_with_verifier(strict=True)
        request = ActionRequest(agent_id="agent-id-test", action="web.search")
        decision = await pdp.evaluate(request, agent=agent)
        assert decision.decision == DecisionStatus.BLOCK
        assert decision.reason == DecisionReason.INVALID_IDENTITY

    @pytest.mark.asyncio
    async def test_pdp_no_verifier_injected_passes_unsigned(self):
        """Without identity_verifier, PDP operates as before (backward-compat)."""
        from backend.app.pdp.engine import PolicyDecisionPoint
        from unittest.mock import MagicMock

        mock_repo = AsyncMock()
        mock_repo.get_contract_for_agent = AsyncMock(return_value=None)
        mock_trust = AsyncMock()
        from backend.app.trust.engine import TrustScore
        _ts2 = TrustScore(agent_id="agent-id-test")
        mock_trust.apply_decision = AsyncMock(return_value=_ts2)
        mock_trust.apply_consistency_violation = AsyncMock(return_value=_ts2)
        mock_qc = AsyncMock()
        mock_qc.maybe_quarantine = AsyncMock()
        mock_provenance = AsyncMock()
        _sink_ok2 = AsyncMock()
        _sink_ok2.is_tainted = False
        _sink_ok2.record = None
        mock_provenance.check_sink = AsyncMock(return_value=_sink_ok2)
        mock_provenance.mark_tainted = AsyncMock()
        mock_drift = MagicMock()
        from backend.app.drift.detector import DriftResult, DriftSeverity
        mock_drift.evaluate = MagicMock(
            return_value=DriftResult(drift_score=0.0, severity=DriftSeverity.NONE, reason="no drift", details={})
        )

        pdp = PolicyDecisionPoint(
            contract_repository=mock_repo,
            identity_verifier=None,  # no verifier injected
            trust_evaluator=mock_trust,
            provenance_evaluator=mock_provenance,
            drift_detector=mock_drift,
            quarantine_controller=mock_qc,
        )
        agent = _make_agent(public_key=None)
        request = ActionRequest(agent_id="agent-id-test", action="read.file")
        decision = await pdp.evaluate(request, agent=agent)
        # Should not be BLOCK due to identity
        assert decision.reason != DecisionReason.INVALID_IDENTITY


# ===========================================================================
# 6: AegisMeshClient signing tests
# ===========================================================================

class TestAegisMeshClientSigning:
    """Tests 18–19: Client auto-signs when private key is present."""

    def test_18_attach_identity_proof_signs_when_key_present(self):
        from agents.common.client import AegisMeshClient
        priv, pub_hex = generate_ed25519_keypair()
        client = AegisMeshClient(private_key=priv)
        body = {
            "agent_id": "agent-x",
            "action": "web.search",
            "payload": {},
        }
        signed = client._attach_identity_proof(body)
        assert "signature" in signed
        assert "timestamp" in signed
        assert "nonce" in signed
        assert len(signed["signature"]) == 128  # 64 bytes hex

    def test_19_attach_identity_proof_noop_without_key(self):
        from agents.common.client import AegisMeshClient
        client = AegisMeshClient()
        body = {"agent_id": "agent-x", "action": "web.search", "payload": {}}
        result = client._attach_identity_proof(body)
        assert result is body  # same object, no copy

    def test_client_signature_verifiable_by_verifier(self):
        """Signature produced by client can be verified by IdentityVerifier's crypto."""
        from agents.common.client import AegisMeshClient
        priv, pub_hex = generate_ed25519_keypair()
        client = AegisMeshClient(private_key=priv)
        body = {
            "agent_id": "agent-x",
            "action": "data.export",
            "payload": {"dest": "s3://bucket"},
        }
        signed = client._attach_identity_proof(body)
        # Reproduce canonical message and verify
        msg = create_canonical_message(
            agent_id=signed["agent_id"],
            action=signed["action"],
            payload=signed["payload"],
            mission_id=signed.get("mission_id"),
            timestamp=signed["timestamp"],
            nonce=signed["nonce"],
        )
        assert verify_ed25519_signature(pub_hex, msg, signed["signature"]) is True

    def test_two_enforce_calls_use_different_nonces(self):
        """Each call must generate a fresh nonce (anti-replay)."""
        from agents.common.client import AegisMeshClient
        priv, _ = generate_ed25519_keypair()
        client = AegisMeshClient(private_key=priv)
        body = {"agent_id": "a", "action": "x", "payload": {}}
        s1 = client._attach_identity_proof(body)
        s2 = client._attach_identity_proof(body)
        assert s1["nonce"] != s2["nonce"]
