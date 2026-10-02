from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from backend.app.db.client import get_supabase_client
from backend.app.schemas.contract import ContractCreate, ContractUpdate, MissionContract
from backend.app.schemas.decision import RiskLevel

logger = logging.getLogger("aegismesh.contracts.repository")


def get_default_seed_contracts() -> List[MissionContract]:
    """
    Deterministic seed mission contracts for the foundational demonstration agents.
    Enforces principle of least privilege.
    """
    now = datetime.now(timezone.utc)
    return [
        MissionContract(
            id="contract-planner-default",
            mission_id=None,
            agent_id="planner-01",
            name="Lead Planner Strategic Contract",
            description="Authorizes goal decomposition, task delegation, and plan declaration.",
            allowed_tools=[
                "plan.create",
                "plan.declare",
                "task.delegate",
                "objective.decompose",
            ],
            forbidden_tools=[
                "shell.exec",
                "external.post",
                "fs.write",
                "database.export",
                "secret.read",
            ],
            allowed_resources=["memory://plans/*"],
            risk_level=RiskLevel.MEDIUM,
            enabled=True,
            created_at=now,
            updated_at=now,
        ),
        MissionContract(
            id="contract-researcher-default",
            mission_id=None,
            agent_id="researcher-01",
            name="Deep Researcher Intelligence Contract",
            description="Authorizes read-only web searches, page reads, and research database queries.",
            allowed_tools=[
                "web.search",
                "web.read",
                "research_db.read",
            ],
            forbidden_tools=[
                "database.export",
                "shell.exec",
                "external.post",
                "fs.write",
                "secret.read",
            ],
            allowed_resources=["https://*", "internal://research_db/*"],
            risk_level=RiskLevel.LOW,
            enabled=True,
            created_at=now,
            updated_at=now,
        ),
        MissionContract(
            id="contract-executor-default",
            mission_id=None,
            agent_id="executor-01",
            name="Task Executor Synthesis Contract",
            description="Authorizes synthesis of executive reports, markdown summaries, and data reads.",
            allowed_tools=[
                "report.generate",
                "database.read",
                "fs.read",
            ],
            forbidden_tools=[
                "database.export",
                "shell.exec",
                "external.post",
                "fs.write",
                "secret.read",
            ],
            allowed_resources=["fs://reports/*", "db://read_only/*"],
            risk_level=RiskLevel.MEDIUM,
            enabled=True,
            created_at=now,
            updated_at=now,
        ),
    ]


class BaseContractRepository(ABC):
    """Abstract interface for Mission Contracts persistence."""

    @abstractmethod
    async def get_contract_for_agent(
        self, agent_id: str, mission_id: Optional[str] = None
    ) -> Optional[MissionContract]:
        """Retrieves active contract for agent, matching mission_id if specified."""
        pass

    @abstractmethod
    async def get_contract_by_id(self, contract_id: str) -> Optional[MissionContract]:
        """Retrieves contract by its unique ID."""
        pass

    @abstractmethod
    async def create_contract(self, contract: ContractCreate) -> MissionContract:
        """Stores a new mission contract."""
        pass

    @abstractmethod
    async def update_contract(
        self, agent_id: str, update: ContractUpdate, mission_id: Optional[str] = None
    ) -> Optional[MissionContract]:
        """Updates an existing mission contract."""
        pass

    @abstractmethod
    async def list_contracts(self) -> List[MissionContract]:
        """Lists all contracts."""
        pass


class InMemoryContractRepository(BaseContractRepository):
    """In-memory implementation with default seed contracts pre-loaded."""

    def __init__(self, seed: bool = True):
        self._contracts: Dict[str, MissionContract] = {}
        self._lock = asyncio.Lock()
        if seed:
            for c in get_default_seed_contracts():
                self._contracts[c.id] = c

    async def get_contract_for_agent(
        self, agent_id: str, mission_id: Optional[str] = None
    ) -> Optional[MissionContract]:
        async with self._lock:
            # 1. Exact match: agent_id + mission_id + enabled
            if mission_id is not None:
                for c in self._contracts.values():
                    if c.agent_id == agent_id and c.mission_id == mission_id and c.enabled:
                        return c

            # 2. Fallback to default active contract for agent (mission_id is None)
            for c in self._contracts.values():
                if c.agent_id == agent_id and c.mission_id is None and c.enabled:
                    return c

            # 3. Any active contract for agent if none other found
            for c in self._contracts.values():
                if c.agent_id == agent_id and c.enabled:
                    return c

            return None

    async def get_contract_by_id(self, contract_id: str) -> Optional[MissionContract]:
        async with self._lock:
            return self._contracts.get(contract_id)

    async def create_contract(self, contract: ContractCreate) -> MissionContract:
        async with self._lock:
            now = datetime.now(timezone.utc)
            cid = contract.id or f"contract-{contract.agent_id}-{uuid.uuid4().hex[:6]}"
            model = MissionContract(
                id=cid,
                mission_id=contract.mission_id,
                agent_id=contract.agent_id,
                name=contract.name,
                description=contract.description,
                allowed_tools=contract.allowed_tools,
                forbidden_tools=contract.forbidden_tools,
                allowed_resources=contract.allowed_resources,
                risk_level=contract.risk_level,
                enabled=contract.enabled,
                created_at=now,
                updated_at=now,
            )
            self._contracts[cid] = model
            return model

    async def update_contract(
        self, agent_id: str, update: ContractUpdate, mission_id: Optional[str] = None
    ) -> Optional[MissionContract]:
        async with self._lock:
            target: Optional[MissionContract] = None
            for c in self._contracts.values():
                if c.agent_id == agent_id:
                    if mission_id is not None and c.mission_id == mission_id:
                        target = c
                        break
                    elif mission_id is None and c.mission_id is None:
                        target = c
                        break
            if not target:
                for c in self._contracts.values():
                    if c.agent_id == agent_id:
                        target = c
                        break

            if not target:
                return None

            now = datetime.now(timezone.utc)
            updated_dict = target.model_dump()
            patch = update.model_dump(exclude_unset=True, exclude_none=True)
            updated_dict.update(patch)
            updated_dict["updated_at"] = now
            updated = MissionContract.model_validate(updated_dict)
            self._contracts[target.id] = updated
            return updated

    async def list_contracts(self) -> List[MissionContract]:
        async with self._lock:
            return list(self._contracts.values())


class SupabaseContractRepository(BaseContractRepository):
    """Supabase PostgreSQL implementation of Mission Contracts with fallback resilience."""

    def __init__(self, client):
        self.client = client
        self._fallback = InMemoryContractRepository(seed=True)

    async def get_contract_for_agent(
        self, agent_id: str, mission_id: Optional[str] = None
    ) -> Optional[MissionContract]:
        try:
            if mission_id is not None:
                res = (
                    self.client.table("mission_contracts")
                    .select("*")
                    .eq("agent_id", agent_id)
                    .eq("mission_id", mission_id)
                    .eq("enabled", True)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return MissionContract.model_validate(res.data[0])

            # Fallback to default contract without mission_id
            res = (
                self.client.table("mission_contracts")
                .select("*")
                .eq("agent_id", agent_id)
                .is_("mission_id", "null")
                .eq("enabled", True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return MissionContract.model_validate(res.data[0])

            # Any enabled contract
            res = (
                self.client.table("mission_contracts")
                .select("*")
                .eq("agent_id", agent_id)
                .eq("enabled", True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return MissionContract.model_validate(res.data[0])

            return None
        except Exception as exc:
            logger.warning(
                "Supabase contract query failed (%s); falling back to seed contract for '%s'",
                exc,
                agent_id,
            )
            return await self._fallback.get_contract_for_agent(agent_id, mission_id)

    async def get_contract_by_id(self, contract_id: str) -> Optional[MissionContract]:
        try:
            res = (
                self.client.table("mission_contracts")
                .select("*")
                .eq("id", contract_id)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return MissionContract.model_validate(res.data[0])
            return None
        except Exception as exc:
            logger.warning("Supabase contract query by id failed (%s)", exc)
            return await self._fallback.get_contract_by_id(contract_id)

    async def create_contract(self, contract: ContractCreate) -> MissionContract:
        cid = contract.id or f"contract-{contract.agent_id}-{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": cid,
            "mission_id": contract.mission_id,
            "agent_id": contract.agent_id,
            "name": contract.name,
            "description": contract.description,
            "allowed_tools": contract.allowed_tools,
            "forbidden_tools": contract.forbidden_tools,
            "allowed_resources": contract.allowed_resources,
            "risk_level": contract.risk_level.value,
            "enabled": contract.enabled,
            "created_at": now,
            "updated_at": now,
        }
        try:
            res = self.client.table("mission_contracts").insert(data).execute()
            if res.data and len(res.data) > 0:
                return MissionContract.model_validate(res.data[0])
            raise RuntimeError("Failed to insert mission contract into Supabase")
        except Exception as exc:
            logger.warning("Supabase create_contract failed (%s); storing in fallback memory", exc)
            return await self._fallback.create_contract(contract)

    async def update_contract(
        self, agent_id: str, update: ContractUpdate, mission_id: Optional[str] = None
    ) -> Optional[MissionContract]:
        patch = update.model_dump(exclude_unset=True, exclude_none=True)
        if "risk_level" in patch and hasattr(patch["risk_level"], "value"):
            patch["risk_level"] = patch["risk_level"].value
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            query = self.client.table("mission_contracts").update(patch).eq("agent_id", agent_id)
            if mission_id is not None:
                query = query.eq("mission_id", mission_id)
            res = query.execute()
            if res.data and len(res.data) > 0:
                return MissionContract.model_validate(res.data[0])
            return None
        except Exception as exc:
            logger.warning("Supabase update_contract failed (%s); falling back to memory", exc)
            return await self._fallback.update_contract(agent_id, update, mission_id)

    async def list_contracts(self) -> List[MissionContract]:
        try:
            res = self.client.table("mission_contracts").select("*").execute()
            return [MissionContract.model_validate(item) for item in (res.data or [])]
        except Exception as exc:
            logger.warning("Supabase list_contracts failed (%s); falling back to memory", exc)
            return await self._fallback.list_contracts()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_contract_repo_instance: Optional[BaseContractRepository] = None


def get_contract_repository() -> BaseContractRepository:
    """Returns singleton contract repository."""
    global _contract_repo_instance
    if _contract_repo_instance is not None:
        return _contract_repo_instance

    from backend.app.db.repository import get_repository, InMemoryRepository
    main_repo = get_repository()
    if isinstance(main_repo, InMemoryRepository):
        _contract_repo_instance = InMemoryContractRepository(seed=True)
        return _contract_repo_instance

    supabase_client = get_supabase_client()
    if supabase_client:
        logger.info("Using SupabaseContractRepository for mission contracts.")
        _contract_repo_instance = SupabaseContractRepository(supabase_client)
    else:
        logger.info("Using InMemoryContractRepository for mission contracts.")
        _contract_repo_instance = InMemoryContractRepository(seed=True)

    return _contract_repo_instance


def set_contract_repository(repo: BaseContractRepository) -> None:
    """Overrides singleton contract repository (for testing)."""
    global _contract_repo_instance
    _contract_repo_instance = repo
