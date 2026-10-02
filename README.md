# SentinelMesh

**PS002 — Runtime Integrity Enforcement for Multi-Agent Networks**

> A bodyguard for AI agents. SentinelMesh watches them, verifies them, catches hallucinations, stops rogue behavior, gives any single-agent IDE access to a full multi-agent team, and keeps a tamper-proof, replayable audit trail.

---

## Why SentinelMesh?

Multi-agent AI systems are powerful — but unchecked agents can hallucinate dependencies, exfiltrate secrets, collude, drift from goals, and tamper with logs. SentinelMesh provides **continuous runtime monitoring**, **real-time auditing**, and **graduated enforcement** so every agent action is verified, every violation is stopped, and every decision is provable.

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────┐
│  IDE LAYER   VS Code │ Cursor │ Windsurf │ JetBrains │ Cline │
│              (IDE Guard: diagnostics, sidebar, approvals)    │
└──────────────────┬───────────────────────────────────────────┘
                   │  MCP / A2A / REST / LLM proxy
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  AGENT BRIDGE (SMAB)                                         │
│  Discovery │ Router │ Negotiator │ Aggregator │ Trust        │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  MONITORED MULTI-AGENT NETWORK                               │
│  Planner │ Researcher │ Coder │ Tester │ Reviewer │ Security │
└──────────────────┬───────────────────────────────────────────┘
                   │  every action → Policy Enforcement Point
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  INSTRUMENTATION                                             │
│  Agent SDK (Py/TS) │ MCP proxy │ LLM proxy │ shell wrapper  │
│  file watcher │ git hooks                                    │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  RUNTIME INTEGRITY CORE (PS002)                              │
│  Identity │ Signed Event Bus │ Ledger (hash chain + Merkle)  │
│  Policy (OPA) │ Plan Verifier │ Trust Engine                 │
│  Detectors: anomaly, drift, taint, collusion, injection,     │
│             hallucination                                    │
│  Enforcement Controller │ Shadow Simulator │ Snapshots       │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT                                                      │
│  Dashboard (8 views) │ IDE diagnostics │ Alerts │ Forensic   │
│  Replay │ Grafana/Jaeger │ CLI                               │
└──────────────────────────────────────────────────────────────┘
```

**Three planes:** Data (agents, tools, PEPs) · Control (PDP, OPA, trust, enforcement) · Evidence (ledger, replay, dashboard)

---

## Key Capabilities

### Security Controls

| Control | Type | Description |
|---|---|---|
| Agent SDK | **Preventive** | `guard.call()` signs and checks every tool call before execution |
| MCP proxy | **Preventive** | Intercepts IDE-agent tool calls, enforces policy |
| LLM proxy | **Preventive / Detective** | Scans prompts for secrets, checks responses for injection |
| Shell wrapper | **Preventive** | PDP check before every command |
| File watcher | **Detective** | Detects unauthorized writes, triggers revert |
| Git hooks | **Detective / Gate** | Blocks commits with hallucinations, secrets, or insecure code |

### Detection

- **Anomaly detection** — EWMA, Isolation Forest, autoencoder ensemble
- **Semantic drift** — Embedding-based goal and baseline tracking (Qdrant)
- **Taint tracking** — Fingerprint + n-gram provenance from source to sink
- **Collusion detection** — Graph motifs (ping-pong, relay chains, mutual approval)
- **Prompt injection** — Heuristic + classifier + LLM-judge scoring
- **Hallucination checks** — Fake packages, phantom APIs, false test claims, insecure code

### Enforcement Ladder

```
Log → Flag → Throttle → Require Approval → Sandbox → Revert → Halt → Quarantine
```

### Trust Engine

Per-agent trust across four dimensions (compliance, integrity, consistency, claim accuracy) drives automatic tier transitions: **trusted → watched → restricted → quarantined**.

---

## Tech Stack

| Layer | Default | Pluggable |
|---|---|---|
| Agent frameworks | LangGraph | AutoGen, CrewAI |
| Backend | Python 3.11, FastAPI, Pydantic v2 | — |
| Event bus | Redis Streams | NATS JetStream, Kafka |
| Policy engine | OPA (Rego) | Cedar |
| Database | PostgreSQL | TimescaleDB |
| Vector store | Qdrant | Weaviate |
| ML | scikit-learn, River | PyTorch |
| Identity | Ed25519, did:key, capability JWT | SPIFFE/SPIRE |
| Frontend | Next.js, React, Tailwind, shadcn/ui | — |
| IDE | VS Code Extension (TypeScript) | JetBrains (Kotlin) |
| Sandbox | Docker (network-isolated) | gVisor / Firecracker |
| Deployment | Docker Compose | Kubernetes (Helm) |

---

## Threat Model

| Threat | Detection | Enforcement |
|---|---|---|
| Prompt injection / tool misuse | Contract, provenance, injection score | Deny / approval |
| Identity spoofing, forged events | Signatures, hash chain | Reject, alert |
| Agent code tampering | Attestation drift | Halt |
| Privilege escalation via delegation | Delegation intersection | Deny |
| Data exfiltration | Taint tracking | Deny, halt |
| Collusion / loops | Graph motifs (+GNN) | Throttle, quarantine |
| Goal drift | Plan verifier, semantic drift | Flag, deny |
| Faulty / abusive behavior | Anomaly ensemble | Throttle |
| Log tampering / repudiation | Hash chain, Merkle, external anchor | Verify fails |
| Hallucinated dependencies/APIs/claims | Hallucination checks | Block, flag |
| Dangerous commands | Shadow simulation | Deny |
| Unauthorized file changes | PEP, watcher, snapshots | Block / revert |
| Rogue agent in delegated task | Controller + Bridge | Halt, reassign |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (dashboard & IDE extension)
- Redis, PostgreSQL (or use the Compose stack)

### Quick Start

```bash
# Clone
git clone https://github.com/shrivastavanant402-maker/Sentinal.git
cd Sentinal

# Start core services
make run

# Start everything (dashboard, bridge, agents, observability)
make run-full

# Run the attack/benign acceptance suite
make benchmark
```

### LLM Note

Agents in `llm` mode need a model API key (e.g. Gemini). Every demo and attack also has a `scripted` mode that needs no key.

---

## Evaluation Metrics

| Metric | Target |
|---|---|
| Detection latency | < 500 ms |
| Enforcement latency | < 1 s |
| Inline decision latency (p95) | < 100 ms |
| False positive rate | < 10% |
| Attack detection rate | > 90% |
| Hallucination detection rate | > 85% |
| Overhead vs unguarded | < 15% |
| Audit completeness | 100% |
| Replay accuracy | 100% |
| Ledger verify (clean run) | 100% |

---

## Project Structure

```
sentinelmesh/
├── ARCHITECTURE.md          # Single source of truth
├── PROGRESS.md              # Progress tracker
├── core/                    # Runtime integrity core
│   ├── schemas/             # Pydantic models
│   ├── event_bus/           # EventBus interface + Redis Streams
│   ├── identity/            # Ed25519, DID, capability tokens
│   ├── ledger/              # Hash chain + Merkle checkpoints
│   ├── policy/              # OPA client + Rego policies
│   ├── detectors/           # Anomaly, drift, taint, collusion, injection, hallucination
│   ├── trust/               # Trust engine + tier management
│   ├── enforcement/         # Graduated enforcement controller
│   └── api/                 # FastAPI routers + WebSocket
├── bridge/                  # Agent Bridge (SMAB)
├── instrumentation/         # SDK, MCP proxy, LLM proxy, shell wrapper, watchers
├── ide/                     # VS Code extension, JetBrains plugin
├── dashboard/               # Next.js dashboard (8 views)
├── policies/                # Rego policies + tests
├── contracts/               # Per-agent behavioral contracts (YAML)
├── attacks/                 # Attack scripts + benign scenarios
├── benchmark/               # Evaluation harness
└── deploy/                  # Docker Compose, Helm, Grafana, OTel config
```

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Full system design (the single source of truth)
- **[PROGRESS.md](PROGRESS.md)** — Current build status

---

## License

TBD

---

<p align="center"><em>SentinelMesh — because autonomous agents need accountability.</em></p>
