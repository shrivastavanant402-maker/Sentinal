import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("aegismesh.client")


class AegisMeshClient:
    """
    Client used by agents to register and emit events to the AegisMesh PEP/Core.
    Decouples agents from backend storage specifics (Supabase, SQLite, etc.).
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: list[str] | None = None,
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/agents/register"
        payload = {
            "id": agent_id,
            "name": name,
            "role": role,
            "capabilities": capabilities or [],
            "metadata": metadata or {}
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def emit_event(
        self,
        agent_id: str,
        event_type: str,
        action: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/events"
        data = {
            "agent_id": agent_id,
            "event_type": event_type,
            "action": action,
            "payload": payload,
            "session_id": session_id
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/agents/{agent_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

    async def verify_ledger(self) -> Dict[str, Any]:
        url = f"{self.base_url}/ledger/verify"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
