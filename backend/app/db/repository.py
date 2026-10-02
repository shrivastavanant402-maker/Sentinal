import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from backend.app.config import get_settings
from backend.app.db.client import get_supabase_client
from backend.app.ledger.hasher import calculate_content_hash, calculate_event_hash
from backend.app.schemas.agent import AgentCreate, AgentResponse, AgentStatus
from backend.app.schemas.event import EventCreate, EventResponse
from backend.app.schemas.alert import AlertCreate, AlertResponse

logger = logging.getLogger("aegismesh.repository")


class BaseRepository(ABC):
    """
    Abstract interface for AegisMesh persistent storage.
    Ensures security logic is decoupled from storage implementation.
    """

    @abstractmethod
    async def register_agent(self, agent: AgentCreate) -> AgentResponse:
        pass

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[AgentResponse]:
        pass

    @abstractmethod
    async def list_agents(self) -> List[AgentResponse]:
        pass

    @abstractmethod
    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentResponse]:
        pass

    @abstractmethod
    async def get_latest_event(self) -> Optional[EventResponse]:
        pass

    @abstractmethod
    async def store_event(self, event: EventCreate) -> EventResponse:
        pass

    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[EventResponse]:
        pass

    @abstractmethod
    async def list_events(self, limit: int = 100, offset: int = 0) -> List[EventResponse]:
        pass

    @abstractmethod
    async def store_alert(self, alert: AlertCreate) -> AlertResponse:
        pass

    @abstractmethod
    async def list_alerts(self, limit: int = 100) -> List[AlertResponse]:
        pass


class InMemoryRepository(BaseRepository):
    """
    In-memory fallback repository for local testing or when Supabase credentials are not provided.
    Implements identical ledger chaining and schema constraints.
    """

    def __init__(self):
        self.agents: Dict[str, AgentResponse] = {}
        self.events: List[EventResponse] = []
        self.alerts: List[AlertResponse] = []
        self._lock = asyncio.Lock()

    async def register_agent(self, agent: AgentCreate) -> AgentResponse:
        async with self._lock:
            now = datetime.now(timezone.utc)
            if agent.id in self.agents:
                existing = self.agents[agent.id]
                updated = AgentResponse(
                    id=agent.id,
                    name=agent.name,
                    role=agent.role,
                    status=existing.status,
                    trust_score=existing.trust_score,
                    public_key=agent.public_key or existing.public_key,
                    capabilities=agent.capabilities or existing.capabilities,
                    metadata={**existing.metadata, **agent.metadata},
                    created_at=existing.created_at,
                    updated_at=now
                )
                self.agents[agent.id] = updated
                return updated

            resp = AgentResponse(
                id=agent.id,
                name=agent.name,
                role=agent.role,
                status=AgentStatus.ACTIVE,
                trust_score=100.0,
                public_key=agent.public_key,
                capabilities=agent.capabilities,
                metadata=agent.metadata,
                created_at=now,
                updated_at=now
            )
            self.agents[agent.id] = resp
            return resp

    async def get_agent(self, agent_id: str) -> Optional[AgentResponse]:
        async with self._lock:
            return self.agents.get(agent_id)

    async def list_agents(self) -> List[AgentResponse]:
        async with self._lock:
            return list(self.agents.values())

    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentResponse]:
        async with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return None
            updated = AgentResponse(
                id=agent.id,
                name=agent.name,
                role=agent.role,
                status=status,
                trust_score=agent.trust_score,
                public_key=agent.public_key,
                capabilities=agent.capabilities,
                metadata=agent.metadata,
                created_at=agent.created_at,
                updated_at=datetime.now(timezone.utc)
            )
            self.agents[agent_id] = updated
            return updated

    async def get_latest_event(self) -> Optional[EventResponse]:
        async with self._lock:
            if not self.events:
                return None
            return self.events[-1]

    async def store_event(self, event: EventCreate) -> EventResponse:
        settings = get_settings()
        async with self._lock:
            event_id = event.id or str(uuid.uuid4())
            ts = event.timestamp or datetime.now(timezone.utc)

            # 1. Content Hash
            content_hash = calculate_content_hash(
                event_id=event_id,
                agent_id=event.agent_id,
                event_type=event.event_type,
                action=event.action,
                payload=event.payload,
                timestamp=ts,
                session_id=event.session_id,
                decision=event.decision
            )

            # 2. Hash chaining from previous event
            if not self.events:
                seq = 1
                previous_hash = settings.LEDGER_GENESIS_PREV_HASH
            else:
                prev_ev = self.events[-1]
                seq = prev_ev.seq + 1
                previous_hash = prev_ev.event_hash

            # 3. Final Event Hash
            event_hash = calculate_event_hash(
                seq=seq,
                content_hash=content_hash,
                previous_hash=previous_hash,
                timestamp=ts
            )

            now = datetime.now(timezone.utc)
            resp = EventResponse(
                id=event_id,
                seq=seq,
                timestamp=ts,
                agent_id=event.agent_id,
                session_id=event.session_id,
                event_type=event.event_type,
                action=event.action,
                payload=event.payload,
                decision=event.decision,
                previous_hash=previous_hash,
                content_hash=content_hash,
                event_hash=event_hash,
                agent_signature=event.agent_signature,
                core_signature=None,
                created_at=now
            )
            self.events.append(resp)
            return resp

    async def get_event(self, event_id: str) -> Optional[EventResponse]:
        async with self._lock:
            for ev in self.events:
                if ev.id == event_id:
                    return ev
            return None

    async def list_events(self, limit: int = 100, offset: int = 0) -> List[EventResponse]:
        async with self._lock:
            # Return ordered by seq ascending
            return self.events[offset : offset + limit]

    async def store_alert(self, alert: AlertCreate) -> AlertResponse:
        async with self._lock:
            alert_id = alert.id or str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            resp = AlertResponse(
                id=alert_id,
                agent_id=alert.agent_id,
                event_id=alert.event_id,
                severity=alert.severity,
                alert_type=alert.alert_type,
                message=alert.message,
                details=alert.details,
                created_at=now
            )
            self.alerts.append(resp)
            return resp

    async def list_alerts(self, limit: int = 100) -> List[AlertResponse]:
        async with self._lock:
            return self.alerts[:limit]


class SupabaseRepository(BaseRepository):
    """
    Production-ready PostgreSQL repository utilizing Supabase.
    Maintains append-only tamper-resistant ledger chain across restarts.
    """

    def __init__(self, client):
        self.client = client
        self._lock = asyncio.Lock()

    async def register_agent(self, agent: AgentCreate) -> AgentResponse:
        now = datetime.now(timezone.utc).isoformat()
        agent_data = {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "public_key": agent.public_key,
            "capabilities": agent.capabilities,
            "metadata": agent.metadata,
            "updated_at": now
        }
        # Upsert agent
        res = self.client.table("agents").upsert(agent_data).execute()
        if res.data and len(res.data) > 0:
            return AgentResponse.model_validate(res.data[0])
        return await self.get_agent(agent.id)

    async def get_agent(self, agent_id: str) -> Optional[AgentResponse]:
        res = self.client.table("agents").select("*").eq("id", agent_id).execute()
        if res.data and len(res.data) > 0:
            return AgentResponse.model_validate(res.data[0])
        return None

    async def list_agents(self) -> List[AgentResponse]:
        res = self.client.table("agents").select("*").order("created_at").execute()
        return [AgentResponse.model_validate(item) for item in (res.data or [])]

    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentResponse]:
        now = datetime.now(timezone.utc).isoformat()
        res = self.client.table("agents").update({"status": status.value, "updated_at": now}).eq("id", agent_id).execute()
        if res.data and len(res.data) > 0:
            return AgentResponse.model_validate(res.data[0])
        return None

    async def get_latest_event(self) -> Optional[EventResponse]:
        res = self.client.table("events").select("*").order("seq", desc=True).limit(1).execute()
        if res.data and len(res.data) > 0:
            return EventResponse.model_validate(res.data[0])
        return None

    async def store_event(self, event: EventCreate) -> EventResponse:
        settings = get_settings()
        async with self._lock:
            event_id = event.id or str(uuid.uuid4())
            ts = event.timestamp or datetime.now(timezone.utc)

            content_hash = calculate_content_hash(
                event_id=event_id,
                agent_id=event.agent_id,
                event_type=event.event_type,
                action=event.action,
                payload=event.payload,
                timestamp=ts,
                session_id=event.session_id,
                decision=event.decision
            )

            latest = await self.get_latest_event()
            if latest is None:
                seq = 1
                previous_hash = settings.LEDGER_GENESIS_PREV_HASH
            else:
                seq = latest.seq + 1
                previous_hash = latest.event_hash

            event_hash = calculate_event_hash(
                seq=seq,
                content_hash=content_hash,
                previous_hash=previous_hash,
                timestamp=ts
            )

            data = {
                "id": event_id,
                "seq": seq,
                "agent_id": event.agent_id,
                "session_id": event.session_id,
                "event_type": event.event_type,
                "action": event.action,
                "payload": event.payload,
                "decision": event.decision,
                "previous_hash": previous_hash,
                "content_hash": content_hash,
                "event_hash": event_hash,
                "agent_signature": event.agent_signature,
                "timestamp": ts.isoformat()
            }
            res = self.client.table("events").insert(data).execute()
            if res.data and len(res.data) > 0:
                return EventResponse.model_validate(res.data[0])
            raise RuntimeError("Failed to insert event into Supabase")

    async def get_event(self, event_id: str) -> Optional[EventResponse]:
        res = self.client.table("events").select("*").eq("id", event_id).execute()
        if res.data and len(res.data) > 0:
            return EventResponse.model_validate(res.data[0])
        return None

    async def list_events(self, limit: int = 100, offset: int = 0) -> List[EventResponse]:
        res = self.client.table("events").select("*").order("seq", desc=False).range(offset, offset + limit - 1).execute()
        return [EventResponse.model_validate(item) for item in (res.data or [])]

    async def store_alert(self, alert: AlertCreate) -> AlertResponse:
        data = {
            "id": alert.id or str(uuid.uuid4()),
            "agent_id": alert.agent_id,
            "event_id": alert.event_id,
            "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            "alert_type": alert.alert_type,
            "message": alert.message,
            "details": alert.details
        }
        res = self.client.table("alerts").insert(data).execute()
        if res.data and len(res.data) > 0:
            return AlertResponse.model_validate(res.data[0])
        raise RuntimeError("Failed to insert alert into Supabase")

    async def list_alerts(self, limit: int = 100) -> List[AlertResponse]:
        res = self.client.table("alerts").select("*").order("created_at", desc=True).limit(limit).execute()
        return [AlertResponse.model_validate(item) for item in (res.data or [])]


_repository_instance: Optional[BaseRepository] = None


def get_repository() -> BaseRepository:
    """
    Returns repository singleton. Uses Supabase if configured, otherwise InMemory.
    """
    global _repository_instance
    if _repository_instance is not None:
        return _repository_instance

    supabase_client = get_supabase_client()
    if supabase_client:
        logger.info("Using SupabaseRepository for persistent storage.")
        _repository_instance = SupabaseRepository(supabase_client)
    else:
        logger.info("Using InMemoryRepository (Supabase not configured or offline).")
        _repository_instance = InMemoryRepository()

    return _repository_instance


def set_repository(repo: BaseRepository):
    """
    Allows overriding repository (useful for isolated unit testing).
    """
    global _repository_instance
    _repository_instance = repo
