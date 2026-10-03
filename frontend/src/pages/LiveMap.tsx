import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { GraphTopology, GraphNode, GraphEdge, GraphStats } from '../types';
import { fetchGraphTopology } from '../services/api';
import type { View } from '../types/figma';

// ---------------------------------------------------------------------------
// Geometry helpers — force-directed layout computed in JS
// ---------------------------------------------------------------------------
interface NodePosition {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function computeForceLayout(
  nodes: GraphNode[],
  sentinelNode: GraphNode,
  _edges: GraphEdge[],
  width: number,
  height: number,
): Record<string, NodePosition> {
  const positions: Record<string, NodePosition> = {};
  const cx = width / 2;
  const cy = height / 2;

  // Sentinel always at center
  positions[sentinelNode.id] = { x: cx, y: cy, vx: 0, vy: 0 };

  // Arrange agent nodes in a circle around sentinel
  const radius = Math.min(width, height) * 0.32;
  const agentNodes = nodes.filter(n => n.id !== sentinelNode.id);
  agentNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / agentNodes.length - Math.PI / 2;
    positions[node.id] = {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      vx: 0,
      vy: 0,
    };
  });

  return positions;
}

// ---------------------------------------------------------------------------
// SVG icon helpers for nodes
// ---------------------------------------------------------------------------

function getRoleIcon(role: string): string {
  const r = role.toLowerCase();
  if (r.includes('planner') || r.includes('orchestrator')) return '🧠';
  if (r.includes('research') || r.includes('intelligence')) return '🔍';
  if (r.includes('executor') || r.includes('operations')) return '⚡';
  if (r.includes('security')) return '🛡️';
  if (r.includes('pep') || r.includes('core') || r.includes('hub')) return '🏛️';
  return '🤖';
}

function getTrustColor(score: number): string {
  if (score >= 80) return 'var(--success)';
  if (score >= 60) return 'var(--warning)';
  if (score >= 40) return 'var(--critical)';
  return '#e53e3e';
}

function getStatusGlow(status: string, isQuarantined: boolean): string {
  if (isQuarantined) return '0 0 24px 8px rgba(229, 62, 62, 0.5)';
  const s = status.toLowerCase();
  if (s === 'active') return '0 0 20px 6px rgba(52, 118, 83, 0.35)';
  if (s === 'degraded') return '0 0 20px 6px rgba(164, 109, 31, 0.35)';
  return '0 0 16px 4px rgba(100, 100, 120, 0.2)';
}

function getEdgeColor(edgeType: string, severity: string): string {
  if (severity === 'critical') return 'var(--critical)';
  if (severity === 'warning') return 'var(--warning)';
  if (edgeType === 'enforcement') return 'var(--accent)';
  if (edgeType === 'delegation') return 'var(--success)';
  if (edgeType === 'taint_propagation') return 'var(--critical)';
  return 'var(--connector)';
}

// ---------------------------------------------------------------------------
// Animated Edge component
// ---------------------------------------------------------------------------
function AnimatedEdge({
  x1, y1, x2, y2,
  edge,
  isSelected,
  onClick,
}: {
  x1: number; y1: number; x2: number; y2: number;
  edge: GraphEdge;
  isSelected: boolean;
  onClick: () => void;
}) {
  const color = getEdgeColor(edge.edge_type, edge.severity);
  const dashArray = edge.edge_type === 'taint_propagation' ? '6 4' : 'none';
  const opacity = isSelected ? 1 : 0.6;
  const strokeWidth = isSelected ? 3 : edge.severity === 'critical' ? 2.5 : 1.8;

  // Compute midpoint for label
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;

  // Shorten edges so they don't overlap node circles
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const nodeRadius = 44;
  const sx = x1 + (dx / len) * nodeRadius;
  const sy = y1 + (dy / len) * nodeRadius;
  const ex = x2 - (dx / len) * nodeRadius;
  const ey = y2 - (dy / len) * nodeRadius;



  return (
    <g className="graph-edge" onClick={onClick} style={{ cursor: 'pointer' }}>
      {/* Glow effect for selected/critical */}
      {(isSelected || edge.severity === 'critical') && (
        <line
          x1={sx} y1={sy} x2={ex} y2={ey}
          stroke={color}
          strokeWidth={strokeWidth + 4}
          strokeOpacity={0.15}
          strokeLinecap="round"
        />
      )}
      {/* Main line */}
      <line
        x1={sx} y1={sy} x2={ex} y2={ey}
        stroke={color}
        strokeWidth={strokeWidth}
        strokeOpacity={opacity}
        strokeDasharray={dashArray}
        strokeLinecap="round"
      />
      {/* Animated particle along edge */}
      <circle r={edge.severity === 'critical' ? 4 : 3} fill={color} opacity={0.9}>
        <animateMotion
          dur={edge.severity === 'critical' ? '1.5s' : '3s'}
          repeatCount="indefinite"
          path={`M${sx},${sy} L${ex},${ey}`}
        />
      </circle>
      {/* Arrow head */}
      <polygon
        points={`0,-5 10,0 0,5`}
        fill={color}
        opacity={opacity}
        transform={`translate(${ex}, ${ey}) rotate(${Math.atan2(ey - sy, ex - sx) * 180 / Math.PI})`}
      />
      {/* Edge label on hover/select */}
      {isSelected && (
        <g transform={`translate(${mx}, ${my - 10})`}>
          <rect
            x={-50} y={-12} width={100} height={24} rx={6}
            fill="var(--surface)" stroke={color} strokeWidth={1}
            opacity={0.95}
          />
          <text
            textAnchor="middle" dy={5}
            fill="var(--text)" fontSize={10} fontFamily="Inter, sans-serif"
            fontWeight={500}
          >
            {edge.label}
          </text>
        </g>
      )}
    </g>
  );
}

// ---------------------------------------------------------------------------
// Node component
// ---------------------------------------------------------------------------
function GraphNodeComponent({
  node,
  x,
  y,
  isSelected,
  onClick,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  pulseIntensity: _pulseIntensity,
}: {
  node: GraphNode;
  x: number;
  y: number;
  isSelected: boolean;
  onClick: () => void;
  pulseIntensity?: number;
}) {
  const isSentinel = node.id === 'sentinel-core';
  const radius = isSentinel ? 52 : 40;
  const trustColor = getTrustColor(node.trust_score);
  const icon = getRoleIcon(node.role);

  // Trust ring arc
  const trustFraction = node.trust_score / 100;
  const circumference = 2 * Math.PI * (radius + 6);
  const strokeDasharray = `${circumference * trustFraction} ${circumference * (1 - trustFraction)}`;

  return (
    <g
      className={`graph-node ${isSelected ? 'selected' : ''} ${node.is_quarantined ? 'quarantined' : ''}`}
      transform={`translate(${x}, ${y})`}
      onClick={onClick}
      style={{ cursor: 'pointer' }}
    >
      {/* Outer pulse ring for active/sentinel */}
      {(isSentinel || node.status === 'active') && !node.is_quarantined && (
        <circle
          r={radius + 16}
          fill="none"
          stroke={isSentinel ? 'var(--accent)' : trustColor}
          strokeWidth={1.5}
          opacity={0.3}
        >
          <animate
            attributeName="r" values={`${radius + 12};${radius + 22};${radius + 12}`}
            dur={isSentinel ? '2s' : '3s'} repeatCount="indefinite"
          />
          <animate
            attributeName="opacity" values="0.3;0.08;0.3"
            dur={isSentinel ? '2s' : '3s'} repeatCount="indefinite"
          />
        </circle>
      )}

      {/* Quarantine warning pulse */}
      {node.is_quarantined && (
        <circle r={radius + 16} fill="none" stroke="var(--critical)" strokeWidth={2} opacity={0.5}>
          <animate attributeName="r" values={`${radius + 10};${radius + 26};${radius + 10}`} dur="1.2s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.5;0.1;0.5" dur="1.2s" repeatCount="indefinite" />
        </circle>
      )}

      {/* Selection ring */}
      {isSelected && (
        <circle
          r={radius + 10}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={2.5}
          strokeDasharray="6 4"
          opacity={0.8}
        >
          <animateTransform
            attributeName="transform" type="rotate"
            from="0" to="360" dur="8s" repeatCount="indefinite"
          />
        </circle>
      )}

      {/* Trust score arc ring */}
      <circle
        r={radius + 6}
        fill="none"
        stroke={trustColor}
        strokeWidth={3}
        strokeDasharray={strokeDasharray}
        strokeLinecap="round"
        transform="rotate(-90)"
        opacity={0.7}
      />

      {/* Background circle */}
      <circle
        r={radius}
        fill={isSentinel ? 'var(--accent-soft)' : 'var(--surface)'}
        stroke={node.is_quarantined ? 'var(--critical)' : isSentinel ? 'var(--accent-border)' : 'var(--border)'}
        strokeWidth={isSelected ? 2.5 : 1.5}
        filter={isSelected || isSentinel ? `drop-shadow(${getStatusGlow(node.status, node.is_quarantined)})` : undefined}
      />

      {/* Role icon */}
      <text
        textAnchor="middle" dy={isSentinel ? -6 : -4}
        fontSize={isSentinel ? 22 : 18}
        style={{ pointerEvents: 'none' }}
      >
        {icon}
      </text>

      {/* Node name */}
      <text
        textAnchor="middle" dy={isSentinel ? 16 : 14}
        fill="var(--text)" fontSize={isSentinel ? 10 : 9}
        fontFamily="Inter, sans-serif" fontWeight={600}
        style={{ pointerEvents: 'none' }}
      >
        {node.name.length > 16 ? node.name.slice(0, 14) + '…' : node.name}
      </text>

      {/* Trust score badge */}
      <g transform={`translate(${radius - 6}, ${-radius + 6})`}>
        <circle r={12} fill={trustColor} opacity={0.9} />
        <text
          textAnchor="middle" dy={4}
          fill="white" fontSize={8} fontWeight={700}
          fontFamily="JetBrains Mono, monospace"
          style={{ pointerEvents: 'none' }}
        >
          {Math.round(node.trust_score)}
        </text>
      </g>

      {/* Status indicator dot */}
      <circle
        cx={-(radius - 6)} cy={-(radius - 6)}
        r={5}
        fill={node.is_quarantined ? 'var(--critical)' : node.status === 'active' ? 'var(--success)' : 'var(--warning)'}
        stroke="var(--surface)"
        strokeWidth={2}
      />

      {/* Taint indicator */}
      {node.taint_label !== 'CLEAN' && (
        <g transform={`translate(${radius - 6}, ${radius - 6})`}>
          <circle r={9} fill="var(--critical-soft)" stroke="var(--critical)" strokeWidth={1} />
          <text textAnchor="middle" dy={4} fontSize={9} style={{ pointerEvents: 'none' }}>☣</text>
        </g>
      )}

      {/* Event count badge */}
      {node.event_count > 0 && (
        <g transform={`translate(${-(radius - 6)}, ${radius - 6})`}>
          <rect x={-14} y={-9} width={28} height={18} rx={9} fill="var(--surface-muted)" stroke="var(--border)" strokeWidth={1} />
          <text
            textAnchor="middle" dy={4}
            fill="var(--text-2)" fontSize={8} fontWeight={600}
            fontFamily="JetBrains Mono, monospace"
            style={{ pointerEvents: 'none' }}
          >
            {node.event_count > 99 ? '99+' : node.event_count}
          </text>
        </g>
      )}
    </g>
  );
}

// ---------------------------------------------------------------------------
// Stats Bar
// ---------------------------------------------------------------------------
function GraphStatsBar({ stats }: { stats: GraphStats }) {
  const statItems = [
    { label: 'Agents', value: stats.total_agents, color: 'var(--accent)' },
    { label: 'Active', value: stats.active_agents, color: 'var(--success)' },
    { label: 'Quarantined', value: stats.quarantined_agents, color: 'var(--critical)' },
    { label: 'Tainted', value: stats.tainted_agents, color: 'var(--warning)' },
    { label: 'Events', value: stats.total_events, color: 'var(--info)' },
    { label: 'Blocked', value: stats.blocked_actions, color: 'var(--critical)' },
    { label: 'Allowed', value: stats.allowed_actions, color: 'var(--success)' },
    { label: 'Avg Trust', value: `${stats.average_trust}%`, color: getTrustColor(stats.average_trust) },
  ];

  return (
    <div className="graph-stats-bar">
      {statItems.map(item => (
        <div key={item.label} className="graph-stat-item">
          <span className="graph-stat-value" style={{ color: item.color }}>{item.value}</span>
          <span className="graph-stat-label">{item.label}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node Detail Panel
// ---------------------------------------------------------------------------
function NodeDetailPanel({
  node,
  edges,
  onClose,
  go: _go,
}: {
  node: GraphNode;
  edges: GraphEdge[];
  onClose: () => void;
  go: (view: View) => void;
}) {
  const relatedEdges = edges.filter(e => e.source === node.id || e.target === node.id);

  return (
    <div className="graph-detail-panel">
      <div className="graph-detail-header">
        <div className="graph-detail-title-row">
          <span className="graph-detail-icon">{getRoleIcon(node.role)}</span>
          <div>
            <h3>{node.name}</h3>
            <span className="graph-detail-role">{node.role}</span>
          </div>
        </div>
        <button className="graph-detail-close" onClick={onClose} aria-label="Close">✕</button>
      </div>

      <div className="graph-detail-body">
        {/* Status & Trust */}
        <div className="graph-detail-section">
          <div className="graph-detail-row">
            <span className="graph-detail-label">Status</span>
            <span className={`graph-status-badge ${node.is_quarantined ? 'quarantined' : node.status}`}>
              {node.is_quarantined ? '🔒 Quarantined' : node.status.charAt(0).toUpperCase() + node.status.slice(1)}
            </span>
          </div>
          <div className="graph-detail-row">
            <span className="graph-detail-label">Trust Score</span>
            <div className="graph-trust-bar-container">
              <div className="graph-trust-bar" style={{ width: `${node.trust_score}%`, background: getTrustColor(node.trust_score) }} />
              <span className="graph-trust-value">{node.trust_score}%</span>
            </div>
          </div>
          <div className="graph-detail-row">
            <span className="graph-detail-label">Trust Tier</span>
            <span className={`graph-tier-badge ${node.trust_tier.toLowerCase()}`}>{node.trust_tier}</span>
          </div>
          <div className="graph-detail-row">
            <span className="graph-detail-label">Taint</span>
            <span className={`graph-taint-badge ${node.taint_label.toLowerCase()}`}>{node.taint_label}</span>
          </div>
          <div className="graph-detail-row">
            <span className="graph-detail-label">Events</span>
            <span className="graph-detail-mono">{node.event_count}</span>
          </div>
        </div>

        {/* Capabilities */}
        <div className="graph-detail-section">
          <h4>Capabilities</h4>
          <div className="graph-capabilities">
            {node.capabilities.map(cap => (
              <span key={cap} className="graph-capability-tag">{cap}</span>
            ))}
          </div>
        </div>

        {/* Connected Edges */}
        <div className="graph-detail-section">
          <h4>Connections ({relatedEdges.length})</h4>
          <div className="graph-edge-list">
            {relatedEdges.map((edge, i) => (
              <div key={i} className={`graph-edge-item ${edge.severity}`}>
                <span className="graph-edge-type-icon">
                  {edge.edge_type === 'enforcement' ? '🛡️' :
                   edge.edge_type === 'delegation' ? '📤' :
                   edge.edge_type === 'taint_propagation' ? '☣️' : '💬'}
                </span>
                <div className="graph-edge-info">
                  <span className="graph-edge-label">{edge.label}</span>
                  <span className="graph-edge-meta">
                    {edge.source === node.id ? `→ ${edge.target}` : `← ${edge.source}`}
                    {' · '}{edge.event_count} events
                  </span>
                </div>
                <span className={`graph-edge-severity-dot ${edge.severity}`} />
              </div>
            ))}
          </div>
        </div>

        {/* Recent Decisions */}
        {node.recent_decisions.length > 0 && (
          <div className="graph-detail-section">
            <h4>Recent Decisions</h4>
            <div className="graph-decisions-list">
              {node.recent_decisions.map((dec, i) => (
                <div key={i} className={`graph-decision-item ${dec.decision.toLowerCase()}`}>
                  <code>{dec.action}</code>
                  <span className={`graph-decision-badge ${dec.decision.toLowerCase()}`}>
                    {dec.decision}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Edge legend
// ---------------------------------------------------------------------------
function GraphLegend() {
  const items = [
    { color: 'var(--accent)', label: 'PEP Enforcement', style: 'solid' },
    { color: 'var(--success)', label: 'Task Delegation', style: 'solid' },
    { color: 'var(--critical)', label: 'Taint Propagation', style: 'dashed' },
    { color: 'var(--connector)', label: 'Data Flow', style: 'solid' },
  ];
  return (
    <div className="graph-legend">
      {items.map(item => (
        <div key={item.label} className="graph-legend-item">
          <svg width={24} height={10}>
            <line
              x1={0} y1={5} x2={24} y2={5}
              stroke={item.color} strokeWidth={2}
              strokeDasharray={item.style === 'dashed' ? '4 3' : 'none'}
            />
          </svg>
          <span>{item.label}</span>
        </div>
      ))}
      <div className="graph-legend-item">
        <span className="graph-legend-dot" style={{ background: 'var(--success)' }} />
        <span>Active</span>
      </div>
      <div className="graph-legend-item">
        <span className="graph-legend-dot" style={{ background: 'var(--critical)' }} />
        <span>Quarantined</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main LiveMap page component
// ---------------------------------------------------------------------------
export function LiveMap({ go }: { go: (view: View) => void }) {
  const [topology, setTopology] = useState<GraphTopology | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [_isLoading, setIsLoading] = useState(true);
  const [_error, setError] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);

  // Auto-refresh topology
  const loadTopology = useCallback(async () => {
    try {
      const data = await fetchGraphTopology();
      setTopology(data);
      setError(null);
      setIsLoading(false);
    } catch (err: any) {
      // If we already have data, keep it; only show error on first load
      if (!topology) {
        setError(err.message || 'Failed to load graph');
      }
      setIsLoading(false);
    }
  }, [topology]);

  useEffect(() => {
    loadTopology();
    if (!isPaused) {
      const timer = setInterval(loadTopology, 4000);
      return () => clearInterval(timer);
    }
  }, [isPaused]);

  // Layout positions (computed but used via activePositions)
  useMemo(() => {
    if (!topology) return {};
    const width = 900;
    const height = 600;
    const allNodes = [...topology.nodes, topology.sentinel_node];
    return computeForceLayout(allNodes, topology.sentinel_node, topology.edges, width, height);
  }, [topology]);

  const selectedNode = useMemo(() => {
    if (!topology || !selectedNodeId) return null;
    if (selectedNodeId === topology.sentinel_node.id) return topology.sentinel_node;
    return topology.nodes.find(n => n.id === selectedNodeId) || null;
  }, [topology, selectedNodeId]);

  // Fallback with seed data when backend is offline
  const fallbackTopology = useMemo((): GraphTopology => ({
    nodes: [
      { id: 'planner-01', name: 'Planner Agent', role: 'Orchestrator', status: 'active', trust_score: 97, trust_tier: 'TRUSTED', taint_label: 'CLEAN', capabilities: ['plan.declare', 'task.delegate'], recent_decisions: [{ action: 'task.delegate', decision: 'ALLOW', risk_level: 'low', event_type: 'tool_call_request' }], event_count: 12, last_action: 'task.delegate', last_event_time: null, is_quarantined: false },
      { id: 'researcher-01', name: 'Researcher Agent', role: 'Intelligence', status: 'quarantined', trust_score: 34, trust_tier: 'QUARANTINED', taint_label: 'UNTRUSTED', capabilities: ['web.search', 'web.read'], recent_decisions: [{ action: 'database.export', decision: 'BLOCK', risk_level: 'critical', event_type: 'enforcement' }], event_count: 24, last_action: 'database.export', last_event_time: null, is_quarantined: true },
      { id: 'executor-01', name: 'Executor Agent', role: 'Operations', status: 'active', trust_score: 96, trust_tier: 'TRUSTED', taint_label: 'CLEAN', capabilities: ['report.generate', 'fs.read'], recent_decisions: [{ action: 'report.generate', decision: 'ALLOW', risk_level: 'low', event_type: 'tool_call_request' }], event_count: 8, last_action: 'report.generate', last_event_time: null, is_quarantined: false },
    ],
    edges: [
      { source: 'planner-01', target: 'sentinel-core', label: 'PEP Enforcement', edge_type: 'enforcement', severity: 'normal', event_count: 12, last_event_time: null, metadata: {} },
      { source: 'researcher-01', target: 'sentinel-core', label: 'PEP Enforcement', edge_type: 'enforcement', severity: 'critical', event_count: 24, last_event_time: null, metadata: { quarantined: true } },
      { source: 'executor-01', target: 'sentinel-core', label: 'PEP Enforcement', edge_type: 'enforcement', severity: 'normal', event_count: 8, last_event_time: null, metadata: {} },
      { source: 'planner-01', target: 'researcher-01', label: 'Task Delegation', edge_type: 'delegation', severity: 'normal', event_count: 3, last_event_time: null, metadata: {} },
      { source: 'planner-01', target: 'executor-01', label: 'Task Delegation', edge_type: 'delegation', severity: 'normal', event_count: 2, last_event_time: null, metadata: {} },
      { source: 'researcher-01', target: 'executor-01', label: 'Data Handoff', edge_type: 'delegation', severity: 'warning', event_count: 1, last_event_time: null, metadata: {} },
    ],
    stats: {
      total_agents: 3, active_agents: 2, quarantined_agents: 1,
      total_events: 44, total_edges: 6, blocked_actions: 5,
      allowed_actions: 39, tainted_agents: 1, average_trust: 75.7,
      last_updated: new Date().toISOString(),
    },
    sentinel_node: {
      id: 'sentinel-core', name: 'SentinelMesh Core', role: 'PEP Hub', status: 'active',
      trust_score: 100, trust_tier: 'CORE', taint_label: 'CLEAN',
      capabilities: ['policy.enforce', 'ledger.verify', 'trust.evaluate', 'taint.track'],
      recent_decisions: [], event_count: 44, last_action: 'policy.enforce',
      last_event_time: null, is_quarantined: false,
    },
  }), []);

  const activeTopology = topology || fallbackTopology;
  const activePositions = useMemo(() => {
    const width = 900;
    const height = 600;
    const allNodes = [...activeTopology.nodes, activeTopology.sentinel_node];
    return computeForceLayout(allNodes, activeTopology.sentinel_node, activeTopology.edges, width, height);
  }, [activeTopology]);

  return (
    <div className="livemap-page">
      {/* Page Header */}
      <section className="page-header">
        <div>
          <div className="breadcrumb">Network Intelligence</div>
          <div className="page-title">Live Agent Map</div>
          <div className="page-description">
            Real-time visualization of multi-agent network topology, trust relationships, taint propagation, and PEP enforcement flows.
          </div>
        </div>
        <div className="header-actions">
          <button
            className={`button ${isPaused ? 'secondary' : 'ghost'}`}
            onClick={() => setIsPaused(!isPaused)}
            title={isPaused ? 'Resume live updates' : 'Pause live updates'}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button className="button ghost" onClick={loadTopology} title="Force refresh">
            🔄 Refresh
          </button>
        </div>
      </section>

      {/* Stats Bar */}
      <GraphStatsBar stats={activeTopology.stats} />

      {/* Main Graph Area */}
      <div className="livemap-container">
        <div className="livemap-canvas-wrap">
          {/* Background grid pattern */}
          <svg
            ref={svgRef}
            className="livemap-svg"
            viewBox="0 0 900 600"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--border)" strokeWidth="0.4" opacity="0.4" />
              </pattern>
              <radialGradient id="center-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.08" />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
              </radialGradient>
              {/* Glow filters */}
              <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feFlood floodColor="var(--success)" floodOpacity="0.3" />
                <feComposite in2="blur" operator="in" />
                <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feFlood floodColor="var(--critical)" floodOpacity="0.4" />
                <feComposite in2="blur" operator="in" />
                <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            {/* Background */}
            <rect width="900" height="600" fill="url(#grid)" />
            <circle cx="450" cy="300" r="250" fill="url(#center-glow)" />

            {/* Edges */}
            <g className="edges-layer">
              {activeTopology.edges.map((edge, _i) => {
                const p1 = activePositions[edge.source];
                const p2 = activePositions[edge.target];
                if (!p1 || !p2) return null;
                return (
                  <AnimatedEdge
                    key={`${edge.source}-${edge.target}-${edge.edge_type}`}
                    x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                    edge={edge}
                    isSelected={selectedEdge === edge}
                    onClick={() => setSelectedEdge(selectedEdge === edge ? null : edge)}
                  />
                );
              })}
            </g>

            {/* Sentinel Core Node */}
            {activePositions[activeTopology.sentinel_node.id] && (
              <GraphNodeComponent
                node={activeTopology.sentinel_node}
                x={activePositions[activeTopology.sentinel_node.id].x}
                y={activePositions[activeTopology.sentinel_node.id].y}
                isSelected={selectedNodeId === activeTopology.sentinel_node.id}
                onClick={() => setSelectedNodeId(
                  selectedNodeId === activeTopology.sentinel_node.id ? null : activeTopology.sentinel_node.id
                )}
                pulseIntensity={1}
              />
            )}

            {/* Agent Nodes */}
            {activeTopology.nodes.map(node => {
              const pos = activePositions[node.id];
              if (!pos) return null;
              return (
                <GraphNodeComponent
                  key={node.id}
                  node={node}
                  x={pos.x}
                  y={pos.y}
                  isSelected={selectedNodeId === node.id}
                  onClick={() => setSelectedNodeId(selectedNodeId === node.id ? null : node.id)}
                  pulseIntensity={node.event_count / 10}
                />
              );
            })}
          </svg>

          {/* Legend */}
          <GraphLegend />

          {/* Live indicator */}
          <div className="livemap-live-badge">
            <span className={`livemap-live-dot ${isPaused ? 'paused' : ''}`} />
            {isPaused ? 'Paused' : 'Live'}
          </div>
        </div>

        {/* Detail Panel */}
        {selectedNode && (
          <NodeDetailPanel
            node={selectedNode}
            edges={activeTopology.edges}
            onClose={() => setSelectedNodeId(null)}
            go={go}
          />
        )}
      </div>
    </div>
  );
}
