import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("aegismesh.client")


class AegisMeshClient:
    """
    Client used by agents to communicate with AegisMesh PEP and backend Core.
    Decouples agents from backend storage specifics (Supabase, SQLite, etc.).
    Supports both direct network HTTP calls and in-process ASGI test transport.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        app: Optional[Any] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._app = app
        self._transport = transport
        self.timeout = timeout

    def _create_http_client(self) -> httpx.AsyncClient:
        """Creates an httpx client respecting any injected ASGI app or transport."""
        transport = self._transport
        app = getattr(self, "_app", None)
        if transport is None and app is not None:
            transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(
            base_url=self.base_url,
            transport=transport,
            timeout=self.timeout,
        )

    async def enforce(self, action_request: Any) -> Dict[str, Any]:
        """
        Sends an ActionRequest to the PEP /enforce endpoint.
        Returns the parsed decision response dictionary.
        Raises httpx.HTTPError if request fails or server returns error.
        """
        url = f"{self.base_url}/enforce"
        if hasattr(action_request, "model_dump"):
            body = action_request.model_dump(mode="json", exclude_none=True)
        elif isinstance(action_request, dict):
            body = action_request
        else:
            raise ValueError(f"Unsupported action_request type: {type(action_request)}")

        async with self._create_http_client() as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: list[str] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/agents/register"
        payload = {
            "id": agent_id,
            "name": name,
            "role": role,
            "capabilities": capabilities or [],
            "metadata": metadata or {},
        }
        async with self._create_http_client() as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def emit_event(
        self,
        agent_id: str,
        event_type: str,
        action: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/events"
        data = {
            "agent_id": agent_id,
            "event_type": event_type,
            "action": action,
            "payload": payload,
            "session_id": session_id,
        }
        async with self._create_http_client() as client:
            resp = await client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/agents/{agent_id}"
        async with self._create_http_client() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

    async def verify_ledger(self) -> Dict[str, Any]:
        url = f"{self.base_url}/ledger/verify"
        async with self._create_http_client() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
