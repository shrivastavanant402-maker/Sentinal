"""
Agent Network Graph API — AegisMesh Live Map

Aggregates agents, trust scores, taint status, recent events,
and inter-agent communication into a single graph topology payload
consumed by the frontend Live Map visualization.

Endpoints:
    GET /graph/topology  — full node + edge graph for live rendering
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.app.db.repository import get_repository
from backend.app.trust.engine import get_trust_engine
from backend.app.provenance.tracker import get_provenance_tracker
from backend.app.enforcement.quarantine import get_quarantine_controller

logger = logging.getLogger("aegismesh.api.graph")

router = APIRouter(prefix="/graph", tags=["Graph"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    name: str
    role: str
    status: str
    trust_score: float
    trust_tier: str
    taint_label: str
    capabilities: List[str]
    recent_decisions: List[Dict[str, Any]]
    event_count: int
    last_action: Optional[str] = None
    last_event_time: Optional[str] = None
    is_quarantined: bool = False


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    edge_type: str  # "delegation", "taint_propagation", "communication", "enforcement"
    severity: str   # "normal", "warning", "critical"
    event_count: int
    last_event_time: Optional[str] = None
    metadata: Dict[str, Any] = {}


class GraphStats(BaseModel):
    total_agents: int
    active_agents: int
    quarantined_agents: int
    total_events: int
    total_edges: int
    blocked_actions: int
    allowed_actions: int
    tainted_agents: int
    average_trust: float
    last_updated: str


class GraphTopology(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: GraphStats
    sentinel_node: GraphNode  # The central SentinelMesh core node


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/topology", response_model=GraphTopology, summary="Get full agent network graph topology")
async def get_graph_topology(
    event_limit: int = Query(200, ge=1, le=1000, description="Max events to analyze for edge computation"),
) -> GraphTopology:
    """
    Compute and return the full network graph topology including:
    - Agent nodes with trust, taint, status metadata
    - Communication/delegation edges derived from event flow
    - A central SentinelMesh core node acting as PEP hub
    - Aggregate stats for the graph header
    """
    repo = get_repository()
    trust_engine = get_trust_engine()
    provenance = get_provenance_tracker()
    quarantine = get_quarantine_controller()

    # Fetch core data
    agents = await repo.list_agents()
    events = await repo.list_events(limit=event_limit, offset=0)
    quarantined_ids = await quarantine.list_quarantined()
    all_trust = await trust_engine.all_scores()

    # Build nodes
    nodes: List[GraphNode] = []
    agent_event_counts: Dict[str, int] = {}
    agent_last_action: Dict[str, str] = {}
    agent_last_time: Dict[str, str] = {}
    agent_decisions: Dict[str, List[Dict[str, Any]]] = {}

    # Helper to convert any value to string safely (datetime, etc.)
    def _str_or_none(val: Any) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, str):
            return val
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val)

    # Count events per agent and track decisions
    for evt in events:
        aid = evt.agent_id
        agent_event_counts[aid] = agent_event_counts.get(aid, 0) + 1
        if aid not in agent_last_action:
            agent_last_action[aid] = evt.action
            raw_time = evt.timestamp if hasattr(evt, 'timestamp') else evt.created_at
            agent_last_time[aid] = _str_or_none(raw_time)
        if aid not in agent_decisions:
            agent_decisions[aid] = []
        if len(agent_decisions[aid]) < 5:
            decision_data = evt.decision if isinstance(evt.decision, dict) else {}
            agent_decisions[aid].append({
                "action": evt.action,
                "decision": decision_data.get("decision", "UNKNOWN"),
                "risk_level": decision_data.get("risk_level", "low"),
                "event_type": evt.event_type,
            })

    for agent in agents:
        aid = agent.id
        taint_label = await provenance.get_agent_taint(aid)
        trust_data = all_trust.get(aid)

        if trust_data:
            trust_score = trust_data.composite
            trust_tier = trust_data.tier
        else:
            trust_score = agent.trust_score if hasattr(agent, 'trust_score') else 95.0
            trust_tier = "TRUSTED"

        is_q = aid in quarantined_ids or agent.status == "quarantined"

        nodes.append(GraphNode(
            id=aid,
            name=agent.name,
            role=agent.role,
            status="quarantined" if is_q else agent.status,
            trust_score=round(trust_score, 1),
            trust_tier=trust_tier if isinstance(trust_tier, str) else str(trust_tier),
            taint_label=taint_label.value if hasattr(taint_label, 'value') else str(taint_label),
            capabilities=agent.capabilities or [],
            recent_decisions=agent_decisions.get(aid, []),
            event_count=agent_event_counts.get(aid, 0),
            last_action=agent_last_action.get(aid),
            last_event_time=agent_last_time.get(aid),
            is_quarantined=is_q,
        ))

    # Build the central SentinelMesh hub node
    sentinel_node = GraphNode(
        id="sentinel-core",
        name="SentinelMesh Core",
        role="PEP Hub",
        status="active",
        trust_score=100.0,
        trust_tier="CORE",
        taint_label="CLEAN",
        capabilities=["policy.enforce", "ledger.verify", "trust.evaluate", "taint.track"],
        recent_decisions=[],
        event_count=len(events),
        last_action="policy.enforce",
        last_event_time=_str_or_none(events[0].created_at) if events else None,
        is_quarantined=False,
    )

    # Build edges from event patterns
    edges: List[GraphEdge] = []
    edge_tracker: Dict[str, Dict[str, Any]] = {}  # "source->target->type" -> data

    # Every agent has an edge to/from the SentinelMesh core (PEP enforcement)
    for agent in agents:
        aid = agent.id
        evt_count = agent_event_counts.get(aid, 0)
        if evt_count == 0:
            continue

        # Agent -> Sentinel (requests)
        has_blocked = any(
            d.get("decision", "").upper() in ("BLOCK", "DENY", "QUARANTINE")
            for d in agent_decisions.get(aid, [])
        )
        sev = "critical" if aid in quarantined_ids else ("warning" if has_blocked else "normal")
        key_out = f"{aid}->sentinel-core->enforcement"
        edge_tracker[key_out] = {
            "source": aid,
            "target": "sentinel-core",
            "label": "PEP Enforcement",
            "edge_type": "enforcement",
            "severity": sev,
            "event_count": evt_count,
            "last_event_time": agent_last_time.get(aid),
            "metadata": {"blocked": has_blocked, "quarantined": aid in quarantined_ids},
        }

    # Detect inter-agent edges from event patterns:
    #   - Planner delegates to Researcher/Executor (delegation edges)
    #   - Taint propagation edges from provenance records
    delegation_agents: Dict[str, List[str]] = {}
    for evt in events:
        action = (evt.action or "").lower()
        agent_id = evt.agent_id
        payload = evt.payload if isinstance(evt.payload, dict) else {}
        target_agent = payload.get("target_agent") or payload.get("delegated_to")

        # Delegation detection
        if "delegate" in action or "assign" in action:
            if target_agent and target_agent != agent_id:
                key = f"{agent_id}->{target_agent}->delegation"
                if key not in edge_tracker:
                    edge_tracker[key] = {
                        "source": agent_id,
                        "target": target_agent,
                        "label": "Task Delegation",
                        "edge_type": "delegation",
                        "severity": "normal",
                        "event_count": 0,
                        "last_event_time": _str_or_none(evt.created_at),
                        "metadata": {},
                    }
                edge_tracker[key]["event_count"] += 1

        # Communication detection (agent sends data to another)
        if "message" in action or "send" in action or "report" in action:
            if target_agent and target_agent != agent_id:
                key = f"{agent_id}->{target_agent}->communication"
                if key not in edge_tracker:
                    edge_tracker[key] = {
                        "source": agent_id,
                        "target": target_agent,
                        "label": "Data Flow",
                        "edge_type": "communication",
                        "severity": "normal",
                        "event_count": 0,
                        "last_event_time": _str_or_none(evt.created_at),
                        "metadata": {},
                    }
                edge_tracker[key]["event_count"] += 1

    # Add taint propagation edges from provenance tracker
    taint_records = await provenance.all_records()
    for record in taint_records:
        path = record.propagation_path or []
        for i in range(len(path) - 1):
            src, dst = path[i], path[i + 1]
            key = f"{src}->{dst}->taint_propagation"
            if key not in edge_tracker:
                edge_tracker[key] = {
                    "source": src,
                    "target": dst,
                    "label": f"Taint: {record.label.value}" if hasattr(record.label, 'value') else f"Taint: {record.label}",
                    "edge_type": "taint_propagation",
                    "severity": "critical" if record.is_hit else "warning",
                    "event_count": 0,
                    "last_event_time": record.created_at.isoformat() if record.created_at else None,
                    "metadata": {
                        "taint_label": record.label.value if hasattr(record.label, 'value') else str(record.label),
                        "is_hit": record.is_hit,
                        "source_tool": record.source_tool,
                    },
                }
            edge_tracker[key]["event_count"] += 1

    # If no inter-agent edges found from events, add inferred delegation edges
    # based on the known agent architecture (planner → researcher → executor)
    agent_ids = {a.id for a in agents}
    inferred_pairs = [
        ("planner-01", "researcher-01", "Task Delegation"),
        ("planner-01", "executor-01", "Task Delegation"),
        ("researcher-01", "executor-01", "Data Handoff"),
    ]
    for src, dst, lbl in inferred_pairs:
        if src in agent_ids and dst in agent_ids:
            key = f"{src}->{dst}->delegation"
            if key not in edge_tracker:
                edge_tracker[key] = {
                    "source": src,
                    "target": dst,
                    "label": lbl,
                    "edge_type": "delegation",
                    "severity": "normal",
                    "event_count": 1,
                    "last_event_time": None,
                    "metadata": {"inferred": True},
                }

    edges = [GraphEdge(**data) for data in edge_tracker.values()]

    # Compute stats
    blocked_count = sum(
        1 for evt in events
        if isinstance(evt.decision, dict) and
        evt.decision.get("decision", "").upper() in ("BLOCK", "DENY", "QUARANTINE")
    )
    allowed_count = sum(
        1 for evt in events
        if isinstance(evt.decision, dict) and
        evt.decision.get("decision", "").upper() == "ALLOW"
    )
    tainted_count = 0
    for agent in agents:
        label = await provenance.get_agent_taint(agent.id)
        lv = label.value if hasattr(label, 'value') else str(label)
        if lv != "CLEAN":
            tainted_count += 1

    trust_scores = [n.trust_score for n in nodes]
    avg_trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0.0

    stats = GraphStats(
        total_agents=len(nodes),
        active_agents=sum(1 for n in nodes if n.status == "active"),
        quarantined_agents=len(quarantined_ids),
        total_events=len(events),
        total_edges=len(edges),
        blocked_actions=blocked_count,
        allowed_actions=allowed_count,
        tainted_agents=tainted_count,
        average_trust=round(avg_trust, 1),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )

    return GraphTopology(
        nodes=nodes,
        edges=edges,
        stats=stats,
        sentinel_node=sentinel_node,
    )
