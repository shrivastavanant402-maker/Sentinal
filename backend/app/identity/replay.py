"""
Replay Protection Cache — AegisMesh Identity & Hardening

Security Limitation Notice:
    This ReplayCache is an in-process, memory-bounded cache local to the single backend
    process instance. In distributed or multi-worker production deployments, this must
    be backed by an atomic distributed cache (e.g. Valkey/Redis or database table)
    to enforce anti-replay across horizontally scaled process boundaries.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger("aegismesh.identity.replay")


class ReplayCache:
    """
    Thread-safe in-process bounded cache for request nonces with TTL expiration.
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: float = 300.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        # nonce -> expiration_timestamp (float)
        self._seen: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def check_and_record(
        self,
        nonce: str,
        request_timestamp: float,
        now: Optional[float] = None,
    ) -> bool:
        """
        Atomically checks if the nonce has already been seen or is expired.
        If fresh, records the nonce and returns True.
        If replayed or expired, returns False.
        """
        if not nonce:
            return False

        current_time = time.time() if now is None else now

        async with self._lock:
            # 1. Prune expired nonces if cache approaches limit
            if len(self._seen) >= self.max_size:
                self._prune_expired(current_time)

            # 2. Check if nonce is already present in cache
            if nonce in self._seen:
                exp = self._seen[nonce]
                if current_time <= exp:
                    logger.warning("Replay attack detected: nonce '%s' already seen (expires in %.1fs)", nonce, exp - current_time)
                    return False
                else:
                    # Expired entry can be overwritten
                    pass

            # 3. Check request timestamp age
            age = abs(current_time - request_timestamp)
            if age > self.ttl_seconds:
                logger.warning("Request expired: age=%.1fs exceeds TTL=%.1fs (nonce=%s)", age, self.ttl_seconds, nonce)
                return False

            # 4. Record nonce with expiration time
            self._seen[nonce] = current_time + self.ttl_seconds
            return True

    def _prune_expired(self, current_time: float) -> None:
        """Remove all nonces whose TTL has passed."""
        expired = [k for k, exp in self._seen.items() if exp < current_time]
        for k in expired:
            del self._seen[k]

    async def clear(self) -> None:
        """Reset the replay cache (used in test isolation)."""
        async with self._lock:
            self._seen.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._seen)


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

_replay_cache_instance: Optional[ReplayCache] = None


def get_replay_cache() -> ReplayCache:
    global _replay_cache_instance
    if _replay_cache_instance is None:
        _replay_cache_instance = ReplayCache()
    return _replay_cache_instance


def set_replay_cache(cache: ReplayCache) -> None:
    global _replay_cache_instance
    _replay_cache_instance = cache
