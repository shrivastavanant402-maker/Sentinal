from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

import httpx
from mcp.server.mcpserver import MCPServer

from backend.app.schemas.decision import ActionRequest, DecisionResponse

# Configure logging strictly to sys.stderr to avoid corrupting stdio MCP protocol stream on stdout
logger = logging.getLogger("aegismesh.mcp")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def create_mcp_server(
    server_name: str = "aegismesh-mcp",
    backend_url: Optional[str] = None,
    in_process: bool = False,
) -> MCPServer:
    """
    Creates and configures the AegisMesh MCP server exposing the `aegismesh_enforce` tool.

    Security Boundary:
      The MCP server does NOT execute tools and does NOT implement its own policy rules.
      All actions submitted to `aegismesh_enforce` are translated into an `ActionRequest`
      and routed through the existing Policy Enforcement Point (PEP) pipeline:
        Identity -> Mission Contract -> Policy Engine -> Trust -> Enforcement -> Ledger

    Args:
        server_name: Identifier for the MCP server.
        backend_url: URL of the running AegisMesh backend API (defaults to env AEGISMESH_URL
                     or http://127.0.0.1:8000).
        in_process: If True, calls the backend `execute_enforcement()` Python function
                    directly without network I/O (ideal for testing).
    """
    server = MCPServer(server_name)
    resolved_backend_url = backend_url or os.getenv("AEGISMESH_URL", "http://127.0.0.1:8000")

    @server.tool(
        name="aegismesh_enforce",
        description=(
            "Enforces AegisMesh runtime security policy on an autonomous agent action. "
            "Evaluates agent identity, mission contract bounds, and risk policy, "
            "recording a cryptographic ledger event before returning the decision "
            "(ALLOW, BLOCK, APPROVAL, QUARANTINE). Call this before executing any tool."
        ),
    )
    async def aegismesh_enforce(
        agent_id: str = "ide-agent-01",
        action: str = "shell.exec",
        payload: Optional[Dict[str, Any]] = None,
        command: Optional[str] = None,
        mission_id: Optional[str] = None,
        session_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submits an agent action to the AegisMesh PEP gate and returns the authoritative decision.
        """
        effective_agent_id = agent_id or "ide-agent-01"
        effective_payload = dict(payload or {})
        if command and "command" not in effective_payload:
            effective_payload["command"] = command

        action_request = ActionRequest(
            agent_id=effective_agent_id,
            action=action,
            payload=effective_payload,
            mission_id=mission_id,
            session_id=session_id,
            provenance=provenance,
        )

        logger.info(
            "MCP aegismesh_enforce request: agent=%s action=%s mission=%s",
            agent_id,
            action,
            mission_id,
        )

        # ── 1. If configured for in-process or forced offline, call execute_enforcement directly
        if in_process or os.getenv("AEGISMESH_USE_IN_PROCESS", "0") == "1":
            from backend.app.api.enforcement import execute_enforcement

            decision: DecisionResponse = await execute_enforcement(action_request)
            return _format_decision(decision)

        # ── 2. Otherwise communicate via HTTP with running AegisMesh Core backend
        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                url = f"{resolved_backend_url.rstrip('/')}/enforce"
                resp = await http_client.post(
                    url,
                    json=action_request.model_dump(exclude_none=True),
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "decision": data.get("decision"),
                    "allowed": data.get("allowed"),
                    "reason": data.get("reason"),
                    "risk_level": data.get("risk_level"),
                    "agent_id": data.get("agent_id"),
                    "action": data.get("action"),
                    "event_id": data.get("event_id"),
                    "details": data.get("details", {}),
                }
        except httpx.ConnectError:
            # Fallback to direct in-process execution if local daemon is not running on network port
            logger.warning(
                "AegisMesh backend at %s not reachable; executing enforcement in-process.",
                resolved_backend_url,
            )
            from backend.app.api.enforcement import execute_enforcement

            decision: DecisionResponse = await execute_enforcement(action_request)
            return _format_decision(decision)
        except Exception as exc:
            logger.error("Enforcement failed (fail-closed): %s", exc)
            # Fail closed: never grant unauthorized access on communication error
            return {
                "decision": "BLOCK",
                "allowed": False,
                "reason": "PEP_COMMUNICATION_ERROR",
                "risk_level": "high",
                "agent_id": agent_id,
                "action": action,
                "event_id": None,
                "details": {"error": str(exc)},
            }

    @server.tool(
        name="aegismesh_run_mission",
        description=(
            "Coordinates and executes an autonomous multi-agent mission across "
            "Planner -> Researcher -> Executor under strict AegisMesh runtime PEP enforcement. "
            "Every agent action (task delegation, web research, artifact generation) is verified "
            "against active mission contracts, provenance, and security policy rules, logging "
            "cryptographic ledger proof for every step."
        ),
    )
    async def aegismesh_run_mission(
        goal: str,
        mission_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a real multi-agent mission using AegisMesh MissionCoordinator.
        """
        logger.info(
            "MCP aegismesh_run_mission request: goal=%s mission_id=%s session_id=%s",
            goal,
            mission_id,
            session_id,
        )

        # ── 1. If configured for in-process or forced offline, call MissionCoordinator directly
        if in_process or os.getenv("AEGISMESH_USE_IN_PROCESS", "0") == "1":
            from backend.app.main import app
            from backend.app.api.missions import ensure_foundational_agents
            from agents.orchestrator.runner import MissionCoordinator
            from agents.common.client import AegisMeshClient

            await ensure_foundational_agents()
            client = AegisMeshClient(app=app)
            coordinator = MissionCoordinator(client=client)
            result = await coordinator.run_mission(
                goal=goal,
                mission_id=mission_id,
                session_id=session_id,
                raise_on_failure=False,
            )
            return _format_mission_result(result)

        # ── 2. Otherwise communicate via HTTP with running AegisMesh Core backend
        try:
            async with httpx.AsyncClient(timeout=60.0) as http_client:
                url = f"{resolved_backend_url.rstrip('/')}/missions/run"
                payload: Dict[str, Any] = {"goal": goal}
                if mission_id:
                    payload["mission_id"] = mission_id
                if session_id:
                    payload["session_id"] = session_id

                resp = await http_client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            logger.warning(
                "AegisMesh backend at %s not reachable; executing mission in-process.",
                resolved_backend_url,
            )
            from backend.app.main import app
            from backend.app.api.missions import ensure_foundational_agents
            from agents.orchestrator.runner import MissionCoordinator
            from agents.common.client import AegisMeshClient

            await ensure_foundational_agents()
            client = AegisMeshClient(app=app)
            coordinator = MissionCoordinator(client=client)
            result = await coordinator.run_mission(
                goal=goal,
                mission_id=mission_id,
                session_id=session_id,
                raise_on_failure=False,
            )
            return _format_mission_result(result)
        except Exception as exc:
            logger.error("Mission execution failed (fail-closed): %s", exc)
            return {
                "mission_id": mission_id or "mission-failed",
                "session_id": session_id or "session-failed",
                "goal": goal,
                "status": "FAILED",
                "planner_result": None,
                "researcher_result": None,
                "executor_result": None,
                "execution_trace": [],
                "event_ids": [],
                "error": str(exc),
                "error_details": {"exception": type(exc).__name__, "details": str(exc)},
            }

    return server


def _format_decision(decision: DecisionResponse) -> Dict[str, Any]:
    """Helper to convert typed DecisionResponse into dictionary output."""
    return {
        "decision": decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision),
        "allowed": decision.allowed,
        "reason": decision.reason.value if hasattr(decision.reason, "value") else str(decision.reason),
        "risk_level": decision.risk_level.value if hasattr(decision.risk_level, "value") else str(decision.risk_level),
        "agent_id": decision.agent_id,
        "action": decision.action,
        "event_id": decision.event_id,
        "details": decision.details or {},
    }


def _format_mission_result(result: Any) -> Dict[str, Any]:
    """Helper to convert typed MissionResult into dictionary output."""
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)


def run_server(transport: str = "stdio", backend_url: Optional[str] = None):
    """Entry point to run the AegisMesh MCP server process."""
    logger.info("Starting AegisMesh MCP Server on transport '%s'...", transport)
    server = create_mcp_server(backend_url=backend_url)
    server.run(transport=transport)
