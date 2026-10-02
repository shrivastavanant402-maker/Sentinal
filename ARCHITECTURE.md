# AegisMesh --- MVP Architecture

## Autonomous AI Agent Runtime Integrity System

> **This file is the single source of truth for the MVP
> implementation.**
>
> AegisMesh is a runtime security and mission-integrity layer for
> autonomous AI agents. It continuously observes agent actions, verifies
> them against identity, permissions, mission contracts, plans,
> provenance, and behavioral context, and can allow, require approval,
> block, revert, halt, or quarantine an agent while preserving
> cryptographically verifiable evidence.
>
> **Primary demo goal:** compromise one agent, detect the deviation,
> contain only that agent, keep the rest of the workflow alive, replay
> the incident, and verify the evidence.
>
> **Team:** 2 developers. Both work on the `main` branch.
>
> **Implementation principle:** build a real, working vertical slice
> before adding advanced detectors or infrastructure. No fake alerts,
> fake trust scores, hardcoded demo outcomes, or UI-only functionality.

------------------------------------------------------------------------

# 1. Product Definition

## 1.1 One-line definition

**AegisMesh is a digital immune system for autonomous AI agents.**

## 1.2 Technical definition

AegisMesh establishes:

1.  **Who** performed an action.
2.  **What** the agent was supposed to do.
3.  **What** it actually attempted to do.
4.  **What data influenced the action.**
5.  **Whether the action is consistent with the mission and current
    plan.**
6.  **How risky the action is.**
7.  **What enforcement response is appropriate.**
8.  **What cryptographically verifiable evidence remains after the
    event.**

## 1.3 Core security loop

``` text
Agent
  |
  v
Interception / Policy Enforcement Point
  |
  v
Identity + Mission + Plan + Context
  |
  v
Policy / Risk / Integrity Decision
  |
  +---------> ALLOW ---------> Tool
  |
  +---------> APPROVAL ------> Human
  |
  +---------> SANDBOX -------> Shadow execution
  |
  +---------> BLOCK ---------> Tool never executes
  |
  +---------> QUARANTINE ---> Agent isolated
  |
  v
Evidence Ledger
  |
  +--> Dashboard
  +--> Alerts
  +--> Replay
  +--> Merkle proof
  +--> Blockchain trust anchor
```

------------------------------------------------------------------------

# 2. PS002 Requirements Mapping

The MVP must directly demonstrate these requirements:

  -----------------------------------------------------------------------
  PS002 requirement                   AegisMesh implementation
  ----------------------------------- -----------------------------------
  Continuous monitoring               Runtime interceptor + event stream

  Real-time auditing                  Append-only event ledger +
                                      WebSocket

  Verify actions vs expected behavior Mission contracts + OPA + plan
                                      verifier

  Detect drift/tampering/faulty       Mission drift + integrity checks +
  behavior                            anomaly detection

  Identify behavioral anomalies       EWMA baseline + Isolation Forest

  Identify policy violations          OPA + risk engine

  Flag or halt non-compliant agents   Enforcement controller

  Trust and accountability            Agent identity + trust score +
                                      signed evidence + replay
  -----------------------------------------------------------------------

The submitted architecture defines these same PS002 mappings; preserve
them as the core of the implementation.

------------------------------------------------------------------------

# 3. MVP Scope

## 3.1 MUST BUILD

### Runtime

-   Python 3.11
-   FastAPI
-   WebSocket
-   Pydantic
-   Redis Streams
-   PostgreSQL
-   OPA/Rego
-   Docker

### Agents

Build exactly three native demo agents:

``` text
Planner
Researcher
Executor
```

Use LangGraph or a lightweight internal orchestration layer. The
security layer must remain framework-independent.

### Security

-   Agent registration
-   Ed25519 agent identity
-   Short-lived capability token
-   Mission contract
-   Tool interception
-   OPA policy decision
-   Plan verification
-   Mission drift detection
-   Basic behavioral anomaly detection
-   Untrusted-content labeling
-   Taint/provenance tracking
-   Trust score
-   Graduated enforcement
-   Human approval
-   Agent quarantine
-   Snapshot/revert
-   Shadow execution for selected high-risk actions

### Evidence

-   Signed events
-   Hash chain
-   Merkle checkpoints
-   Ledger verification
-   Blockchain/testnet anchor for Merkle roots
-   Forensic replay

### UI

Build five excellent views:

1.  Live Operations
2.  Agent Detail
3.  Incident / Alert Detail
4.  Forensic Replay
5.  Audit Ledger / Blockchain Verification

------------------------------------------------------------------------

# 4. DO NOT BUILD IN MVP

These are future/pluggable capabilities:

-   GNN collusion detector
-   Deep autoencoder
-   SPIFFE/SPIRE
-   Kafka/NATS
-   Kubernetes
-   JetBrains plugin
-   Full enterprise IAM
-   eBPF enforcement
-   Multiple production agent frameworks
-   Full distributed deployment
-   Complex ML training pipeline

Interfaces may be designed for future replacement, but do not let these
delay the working vertical slice.

------------------------------------------------------------------------

# 5. Architecture

## 5.1 Three planes

### Data Plane

Latency-sensitive path:

``` text
Agents
  |
Tools
  |
PEP / Interceptor
```

### Control Plane

Decision-making path:

``` text
Identity
Mission Contract
Plan Verifier
OPA
Risk Engine
Trust Engine
Enforcement Controller
```

### Evidence Plane

Accountability path:

``` text
Event Ledger
Hash Chain
Merkle Checkpoints
Blockchain Anchor
Replay
Dashboard
```

------------------------------------------------------------------------

# 6. High-Level Architecture

``` text
                         ┌──────────────────────┐
                         │      Dashboard       │
                         │ React / Next.js      │
                         └──────────┬───────────┘
                                    │ WebSocket/REST
                                    v
┌────────────────────────────────────────────────────────────────┐
│                         FASTAPI CORE                            │
│                                                                │
│  Agents API   Enforcement API   Alerts API   Replay API       │
│  Ledger API   Policies API      Approvals API Metrics API      │
└──────────────┬─────────────────────────────┬───────────────────┘
               │                             │
               v                             v
        ┌─────────────┐              ┌─────────────┐
        │ Redis       │              │ OPA         │
        │ Streams     │              │ Policy      │
        └──────┬──────┘              └──────┬──────┘
               │                            │
               v                            v
┌────────────────────────────────────────────────────────────────┐
│                      AEGISMESH CORE                            │
│                                                                │
│ Identity │ Contracts │ Plan Verifier │ Risk Engine             │
│ Trust    │ Provenance/Taint │ Drift │ Anomaly │ Enforcement    │
│                                                                │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               v
                    ┌─────────────────────┐
                    │ PostgreSQL Ledger   │
                    │ append-only events  │
                    └─────────┬───────────┘
                              │
                    ┌─────────┴──────────┐
                    v                    v
             Hash Chain             Merkle Tree
                                        |
                                        v
                                Blockchain Anchor
```

------------------------------------------------------------------------

# 7. Agent Runtime

## 7.1 Demo topology

``` text
                 ┌──────────┐
                 │ Planner  │
                 └────┬─────┘
                      |
             ┌────────┴────────┐
             v                 v
       ┌───────────┐     ┌───────────┐
       │ Researcher│     │  Executor │
       └───────────┘     └───────────┘
```

### Planner

Responsibilities: - understand user goal - create execution plan -
delegate work - cannot directly access sensitive tools

### Researcher

Responsibilities: - web search/read - approved research database reads -
return evidence

### Executor

Responsibilities: - transform verified research into final artifact -
run approved local operations - cannot access secrets unless explicitly
authorized

------------------------------------------------------------------------

# 8. Tool Model

MVP tools:

``` text
web.search
web.read
research_db.read
database.read
database.export
external.post
fs.read
fs.write
shell.exec
report.generate
```

Every tool has:

``` yaml
name:
risk:
input_schema:
required_capabilities:
allowed_agents:
sensitivity:
```

Unknown tools are denied by default.

------------------------------------------------------------------------

# 9. Policy Enforcement Point

Every important action must pass through a PEP.

``` python
decision = aegis.guard(
    agent_id="researcher-01",
    session_id=session_id,
    tool="database.export",
    args={"table": "customers"}
)

if decision.allowed:
    execute_tool()
else:
    raise ActionDenied(decision.reason)
```

The PEP must:

1.  create the action event
2.  validate identity/token
3.  collect policy facts
4.  invoke the policy engine
5.  execute obligations
6.  record the decision
7.  return the decision

### Preventive vs detective

Preventive: - SDK - tool interceptor - shell wrapper - MCP proxy if
implemented

Detective: - filesystem watcher - post-action verification - git hook

Never claim a detective control prevented an action.

------------------------------------------------------------------------

# 10. Agent Identity

Each agent gets an Ed25519 keypair.

Registration stores:

``` json
{
  "agent_id": "researcher-01",
  "role": "researcher",
  "public_key": "...",
  "status": "active",
  "trust": 100,
  "contract_version": 1
}
```

Agent-originated events are signed.

The system must reject: - unknown agent - invalid signature - expired
capability token - revoked token - invalid session - attestation
mismatch

------------------------------------------------------------------------

# 11. Capability Tokens

Use short-lived JWTs signed with EdDSA.

Token contains:

``` json
{
  "sub": "researcher-01",
  "session": "sess-001",
  "tools": ["web.search", "web.read"],
  "jti": "...",
  "exp": "..."
}
```

When an agent is halted:

``` text
status = halted
+
token jti revoked
```

Do not rely on UI state alone for enforcement.

------------------------------------------------------------------------

# 12. Mission Contracts

Each agent has a versioned YAML contract.

Example:

``` yaml
agent_id: researcher-01
role: researcher
version: 1

mission:
  description: "Research publicly available information."

allowed_tools:
  - web.search
  - web.read
  - research_db.read

forbidden_tools:
  - database.export
  - external.post
  - payment.execute

fs:
  read_allow:
    - workspace/research/**
  write_allow:
    - workspace/reports/**

http:
  domain_allow:
    - trusted-research.example

risk_levels:
  web.search: low
  web.read: low
  research_db.read: medium
  database.export: critical
  external.post: high

obligations:
  database.export:
    - require_approval
  external.post:
    - require_approval
```

Contracts are: - schema validated - versioned - hashed - compiled into
policy data

Default deny unknown actions.

------------------------------------------------------------------------

# 13. Policy Decision Pipeline

``` text
tool_call_request
       |
       v
1. Identity validation
       |
2. Token validation
       |
3. Agent status
       |
4. Contract lookup
       |
5. Plan state
       |
6. Provenance / taint
       |
7. Mission consistency
       |
8. Behavioral risk
       |
9. OPA policy
       |
10. Obligations
       |
11. Decision event
       |
12. Return ALLOW / APPROVAL / DENY
```

OPA returns:

``` json
{
  "decision": "deny",
  "reason_code": "MISSION_VIOLATION",
  "reason": "Action is outside the researcher's mission.",
  "severity": "high",
  "obligations": ["alert", "trust_penalty"]
}
```

------------------------------------------------------------------------

# 14. Mission Integrity

This is the primary product differentiator.

For every action compare:

``` text
MISSION
   +
PLAN
   +
CURRENT CONTEXT
   +
AGENT CAPABILITIES
        |
        v
EXPECTED ACTION
        |
        v
ACTUAL ACTION
```

Generate:

``` text
mission_alignment_score: 0..1
```

Example:

``` text
Mission:
"Research Redis caching strategies."

Action:
web.search("Redis cache invalidation")

Alignment:
0.96
```

Suspicious:

``` text
Mission:
"Research Redis caching strategies."

Action:
database.export("customers")

Alignment:
0.02
```

------------------------------------------------------------------------

# 15. Plan Verifier

Planner creates:

``` json
{
  "goal": "Research Redis caching strategies",
  "steps": [
    {
      "id": "s1",
      "agent": "researcher",
      "tools": ["web.search", "web.read"]
    },
    {
      "id": "s2",
      "agent": "executor",
      "tools": ["report.generate"]
    }
  ]
}
```

The verifier tracks session state.

An action outside the current plan produces:

``` text
plan_ok = false
```

Repeated deviations increase risk.

------------------------------------------------------------------------

# 16. Mission Drift Detector

MVP implementation:

### Level 1

Rule-based mismatch.

### Level 2

Sentence-transformer embeddings.

Embed: - mission - plan step - recent action description

Compute semantic similarity.

``` text
drift_score =
1 - similarity(mission, action_context)
```

Only run the expensive embedding check when the action is not obviously
valid from the current plan.

Thresholds must be configurable.

------------------------------------------------------------------------

# 17. Behavioral Anomaly Detector

Maintain a rolling baseline per agent.

Features:

``` text
calls / 10 sec
distinct tools
call interval
argument length
path depth
error rate
deny rate
bytes out
new tool flag
new domain flag
```

MVP:

1.  EWMA/z-score
2.  Isolation Forest

Example:

``` text
Normal:
6 calls / 10 sec

Current:
58 calls / 10 sec

Anomaly:
HIGH
```

The detector must return explainable feature contributions.

------------------------------------------------------------------------

# 18. Untrusted Content / Prompt Injection

External content is untrusted by default.

Sources:

``` text
web page
PDF
retrieved document
tool output
external message
memory derived from untrusted source
```

Label:

``` text
untrusted
```

Detect instruction-like content such as: - instruction override - role
change - secret extraction request - policy bypass - exfiltration
request

If:

``` text
untrusted_content
        +
high-risk action
```

then set:

``` text
untrusted_trigger = true
```

Policy may require approval or deny.

------------------------------------------------------------------------

# 19. Provenance and Taint Tracking

Sensitive sources:

``` text
.env
API keys
tokens
PII
secret-labelled tool output
high-entropy credentials
```

When an agent reads sensitive data:

``` text
SECRET
  |
  v
Agent A
  |
  v
Message
  |
  v
Agent B
  |
  v
external.post
```

The taint label propagates.

Sensitive sinks:

``` text
external.post
git.push
shell.exec
unapproved fs.write
external LLM prompt
agent-to-agent message
```

If a tainted value reaches a forbidden sink:

``` text
taint_hit = true
severity = critical
decision = deny
```

The dashboard must display:

``` text
source -> agent -> agent -> sink
```

------------------------------------------------------------------------

# 20. Trust Engine

Every agent has four dimensions:

``` text
compliance
integrity
consistency
claim_accuracy
```

Initial:

``` text
100 / 100 / 100 / 100
```

MVP formula:

``` text
trust =
0.35 * compliance
+ 0.25 * integrity
+ 0.20 * consistency
+ 0.20 * claim_accuracy
```

Clamp to 0..100.

Severity penalties:

``` text
LOW       -5
MEDIUM   -15
HIGH     -30
CRITICAL -50
```

Recovery:

``` text
+1 per 10 consecutive clean allowed actions
```

Trust tiers:

``` text
80-100  TRUSTED
60-79   WATCHED
40-59   RESTRICTED
0-39    QUARANTINED
```

------------------------------------------------------------------------

# 21. Enforcement Controller

Use:

``` text
LOG
 ↓
FLAG
 ↓
THROTTLE
 ↓
REQUIRE APPROVAL
 ↓
SANDBOX
 ↓
REVERT
 ↓
HALT
 ↓
QUARANTINE
```

Rules:

### Low

Log.

### Medium

Alert + throttle.

### High

Approval or sandbox.

### Critical

Block + trust penalty.

### Critical security events

Quarantine immediately.

Examples:

``` text
Secret exfiltration -> quarantine
Forged event -> quarantine
Unauthorized sensitive export -> block/approval
Mission drift -> flag/block depending on risk
Burst anomaly -> throttle
```

Every enforcement action creates an event.

------------------------------------------------------------------------

# 22. Human Approval

Approval object:

``` json
{
  "id": "approval-001",
  "agent_id": "executor-01",
  "tool": "external.post",
  "reason": "External network request",
  "risk": "high",
  "expires_in": 60
}
```

UI:

``` text
HIGH RISK ACTION

Executor-01 wants to call:
external.post

Destination:
api.example.com

Reason:
Upload generated report

[ APPROVE ] [ DENY ]
```

Timeout:

``` text
60 seconds -> DENY
```

Approval decisions must be ledgered.

------------------------------------------------------------------------

# 23. Shadow Simulator

For high-risk shell/filesystem operations:

``` text
Action
  |
  v
Temporary sandbox
  |
  v
Execute safely
  |
  v
Collect:
- file diff
- deleted paths
- network attempts
- process activity
- exit code
  |
  v
Risk evaluator
  |
  +--> SAFE
  |
  +--> UNSAFE
```

MVP Docker configuration:

``` text
--network none
read-only root filesystem
temporary writable overlay
CPU limit
memory limit
time limit
dropped capabilities
```

The simulator does not guarantee safety for external side effects. State
this clearly.

------------------------------------------------------------------------

# 24. Snapshot and Revert

Before medium/high-risk writes:

``` text
snapshot_before
```

Store:

``` text
snapshot_id
event_id
workspace/path metadata
git commit or archive reference
```

If action is later determined unsafe:

``` text
POST /snapshots/{id}/revert
```

Emit:

``` text
revert event
```

------------------------------------------------------------------------

# 25. Hallucination / Claim Verification

Agents may claim:

``` text
"Package installed."
"All tests passed."
"File created."
"API exists."
"Security issue fixed."
```

Convert claims into structured events.

Checks:

### Fake package

Check package registry.

### Fake API

Check repository/LSP/static analysis.

### Fake file

Check filesystem/git tree.

### False test claim

Actually execute tests.

### Insecure code

Run Semgrep/Bandit.

Claim result:

``` json
{
  "claim": "all tests pass",
  "verdict": "contradicted",
  "evidence": "4 tests failed",
  "confidence": 0.99
}
```

False claims reduce `claim_accuracy`.

------------------------------------------------------------------------

# 26. Multi-Agent Delegation

Every delegation must carry:

``` text
delegator
delegate
task
required_capabilities
delegation_chain
trust
permissions
```

Effective permission:

``` text
effective_permissions =
user_permissions
∩
delegator_permissions
∩
delegate_permissions
```

Never allow delegation to increase privilege.

Example:

``` text
Planner
  |
  | "Read customer DB"
  v
Researcher

If Planner cannot read customer DB,
Researcher cannot gain that permission through delegation.
```

------------------------------------------------------------------------

# 27. Collusion Detection --- MVP

Do not use a GNN initially.

Build a NetworkX graph:

``` text
nodes = agents
edges = messages/delegations/data flow
```

Detect:

### Ping-pong

``` text
A -> B -> A -> B -> A
```

### Relay

``` text
A -> B -> C -> external
```

### Delegation widening

Delegate has broader authority than intended.

### Burst fan-out

One agent suddenly contacts many agents.

### Mutual approval

Agents repeatedly approve each other's risky actions.

These become async findings.

------------------------------------------------------------------------

# 28. Cryptographic Evidence Ledger

Canonical event:

``` json
{
  "id": "uuid",
  "seq": 123,
  "timestamp": "...",
  "agent_id": "researcher-01",
  "session_id": "sess-001",
  "type": "tool_call_request",
  "payload": {},
  "decision": {},
  "policy_version": "...",
  "content_hash": "...",
  "prev_hash": "...",
  "hash": "...",
  "agent_signature": "...",
  "core_signature": "..."
}
```

### Event hashing

1.  Build event without:
    -   seq
    -   prev_hash
    -   hash
    -   signatures
2.  Canonical JSON.
3.  SHA-256 -\> `content_hash`.
4.  Agent signs `content_hash`.
5.  Ledger assigns `seq` and `prev_hash`.
6.  Compute event hash.
7.  Core signs event hash.

------------------------------------------------------------------------

# 29. Merkle Checkpoints

Every:

``` text
100 events
OR
30 seconds
```

create:

``` text
Merkle root
```

Checkpoint:

``` json
{
  "from_seq": 1,
  "to_seq": 100,
  "merkle_root": "...",
  "timestamp": "..."
}
```

Store checkpoint in PostgreSQL.

Provide inclusion proof:

``` text
event -> Merkle path -> root
```

------------------------------------------------------------------------

# 30. Blockchain Trust Anchor

Blockchain is NOT the runtime database.

Do NOT write every event to blockchain.

Architecture:

``` text
100 events
    |
    v
Merkle root
    |
    v
Blockchain transaction
```

Store:

``` text
chain_id
transaction_hash
merkle_root
checkpoint_range
timestamp
```

The blockchain proves that a checkpoint existed at/around the anchoring
time and that the recorded root can be independently compared.

For the hackathon, use a low-cost EVM-compatible testnet.

The runtime must still work if the blockchain is temporarily
unavailable. Queue/retry anchors asynchronously.

------------------------------------------------------------------------

# 31. Ledger Verification

`GET /api/v1/ledger/verify`

Check:

``` text
✓ event hashes
✓ hash-chain continuity
✓ agent signatures
✓ core signatures
✓ Merkle roots
✓ checkpoint consistency
✓ blockchain anchor consistency
```

Response:

``` json
{
  "ok": true,
  "checked": 1842,
  "checks": {
    "chain": true,
    "signatures": true,
    "merkle": true,
    "anchor": true
  }
}
```

------------------------------------------------------------------------

# 32. Forensic Replay

A session consists of ordered events.

Replay reconstructs:

``` text
agent state
trust
plan state
taint labels
approvals
decisions
alerts
enforcement
```

UI:

``` text
10:31:01  Agent registered
10:31:03  Plan declared
10:31:04  Web page read
10:31:05  Injection detected
10:31:06  DB export requested
10:31:06  DENIED
10:31:06  Trust 94 -> 64
10:31:07  QUARANTINED
```

Replay must use recorded policy versions for deterministic
re-evaluation.

------------------------------------------------------------------------

# 33. Dashboard

## 33.1 Live Operations

Show:

``` text
Events/sec
Blocked actions
Alerts
Decision p95
Active agents
Quarantined agents
Ledger integrity
```

Graph:

``` text
Planner -> Researcher -> Executor
```

Node color represents trust tier.

------------------------------------------------------------------------

## 33.2 Agent Detail

Show:

``` text
Agent
Role
Status
Trust
Compliance
Integrity
Consistency
Claim Accuracy
Mission
Capabilities
Contract
Recent actions
Violations
```

Actions:

``` text
Halt
Resume
Quarantine
Release
```

------------------------------------------------------------------------

## 33.3 Incident Detail

Show:

``` text
Severity
Agent
Action
Reason
Policy facts
Mission mismatch
Plan mismatch
Provenance
Taint lineage
Evidence
Trust change
Enforcement
```

------------------------------------------------------------------------

## 33.4 Replay

Show:

``` text
timeline scrubber
play/pause
speed
agent graph
event details
alerts
trust changes
taint path
```

------------------------------------------------------------------------

## 33.5 Audit Ledger

Show:

``` text
event sequence
event hash
previous hash
signature
Merkle checkpoint
inclusion proof
blockchain anchor
```

Button:

``` text
VERIFY LEDGER
```

------------------------------------------------------------------------

# 34. API

Base path:

``` text
/api/v1
```

## Agents

``` http
POST   /agents/register
POST   /agents/{id}/heartbeat
GET    /agents
GET    /agents/{id}
POST   /agents/{id}/halt
POST   /agents/{id}/resume
POST   /agents/{id}/release
```

## Enforcement

``` http
POST   /enforce
POST   /events
POST   /llm/check
```

## Approvals

``` http
GET    /approvals
POST   /approvals/{id}/decision
```

## Alerts

``` http
GET    /alerts
GET    /findings
```

## Ledger

``` http
GET    /ledger/events
GET    /ledger/verify
GET    /ledger/checkpoints
GET    /ledger/proof/{seq}
```

## Sessions

``` http
GET    /sessions
GET    /sessions/{id}
GET    /sessions/{id}/replay
GET    /sessions/{id}/graph
GET    /sessions/{id}/taint
```

## Contracts

``` http
GET    /contracts/{agent_id}
PUT    /contracts/{agent_id}
```

## Policies

``` http
GET    /policies
POST   /policies
POST   /policies/simulate
```

## Bridge

``` http
POST   /bridge/tasks
GET    /bridge/tasks/{id}
GET    /bridge/tasks/{id}/trace
GET    /bridge/agents
POST   /bridge/tasks/{id}/cancel
```

## Sandbox

``` http
POST   /shadow/simulate
```

## Snapshots

``` http
GET    /snapshots
POST   /snapshots/{id}/revert
```

## WebSocket

``` text
/ws/stream
```

Events:

``` text
event
alert
finding
trust
agent_status
approval
bridge
checkpoint
enforcement
```

------------------------------------------------------------------------

# 35. PostgreSQL Data Model

Core tables:

``` text
agents
agent_attestations
contracts
policy_bundles
sessions
events
alerts
findings
trust_history
approvals
snapshots
taint_registry
bridge_tasks
checkpoints
blockchain_anchors
```

Important rules:

### events

The application role must not have UPDATE/DELETE permissions.

### contracts

Versioned.

### policy_bundles

Versioned and hashed.

### trust_history

Append-only changes:

``` text
agent_id
old_score
new_score
dimension
reason
event_id
timestamp
```

------------------------------------------------------------------------

# 36. Repository Structure

``` text
aegismesh/
│
├── ARCHITECTURE.md
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── agents.py
│   │   │   ├── enforcement.py
│   │   │   ├── alerts.py
│   │   │   ├── ledger.py
│   │   │   ├── replay.py
│   │   │   ├── policies.py
│   │   │   ├── contracts.py
│   │   │   ├── approvals.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── agent.py
│   │   │   ├── event.py
│   │   │   ├── decision.py
│   │   │   ├── finding.py
│   │   │   ├── alert.py
│   │   │   ├── contract.py
│   │   │   └── plan.py
│   │   │
│   │   ├── identity/
│   │   ├── contracts/
│   │   ├── policy/
│   │   ├── pdp/
│   │   ├── enforcement/
│   │   ├── trust/
│   │   ├── provenance/
│   │   ├── drift/
│   │   ├── anomaly/
│   │   ├── hallucination/
│   │   ├── shadow/
│   │   ├── snapshots/
│   │   ├── replay/
│   │   ├── ledger/
│   │   ├── blockchain/
│   │   ├── bridge/
│   │   └── db/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── agents/
│   ├── common/
│   │   ├── sdk.py
│   │   ├── signing.py
│   │   └── client.py
│   ├── planner/
│   ├── researcher/
│   └── executor/
│
├── policies/
│   ├── base.rego
│   ├── researcher.rego
│   ├── executor.rego
│   └── tests/
│
├── contracts/
│   ├── planner.yaml
│   ├── researcher.yaml
│   └── executor.yaml
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
│
├── attacks/
│   ├── prompt_injection.py
│   ├── secret_exfiltration.py
│   ├── mission_drift.py
│   └── rogue_agent.py
│
├── demos/
│   └── primary_attack/
│
└── docs/
```

------------------------------------------------------------------------

# 37. Interfaces

Build interfaces before vendor-specific implementations.

## EventBus

``` python
class EventBus(Protocol):
    async def publish(topic: str, event: Event) -> None: ...
    async def subscribe(topic: str, group: str): ...
```

Default:

``` text
Redis Streams
```

------------------------------------------------------------------------

## PolicyEngine

``` python
class PolicyEngine(Protocol):
    async def evaluate(context: PolicyContext) -> Decision: ...
```

Default:

``` text
OPA
```

------------------------------------------------------------------------

## AnomalyModel

``` python
class AnomalyModel(Protocol):
    def score(self, features: dict) -> AnomalyResult: ...
```

Default:

``` text
EWMA
IsolationForest
```

------------------------------------------------------------------------

## IdentityProvider

``` python
class IdentityProvider(Protocol):
    def register(...)
    def verify(...)
    def revoke(...)
```

Default:

``` text
Ed25519 + JWT
```

------------------------------------------------------------------------

## Ledger

``` python
class Ledger(Protocol):
    async def append(event: Event) -> StoredEvent: ...
    async def verify() -> VerificationResult: ...
    async def proof(seq: int) -> MerkleProof: ...
```

------------------------------------------------------------------------

## BlockchainAnchor

``` python
class BlockchainAnchor(Protocol):
    async def anchor(merkle_root: str) -> AnchorResult: ...
    async def verify(anchor: Anchor) -> bool: ...
```

The blockchain implementation must never be imported directly by the
runtime policy code.

------------------------------------------------------------------------

# 38. Event Types

MVP:

``` text
agent_registered
heartbeat
attestation
plan_declared
plan_step
tool_call_request
decision
tool_call_result
message
delegation
finding
alert
enforcement
trust_update
approval_requested
approval_resolved
simulation_result
snapshot
revert
bridge_task
bridge_delegation
bridge_result
checkpoint
blockchain_anchor
```

------------------------------------------------------------------------

# 39. Primary Attack Scenarios

These must be real automated demos.

## A1 --- Prompt Injection

``` text
Malicious document
  ->
Researcher reads it
  ->
Injected instruction
  ->
Sensitive tool request
  ->
BLOCK
```

Expected: - untrusted label - policy violation - alert - trust
reduction - quarantine if critical

------------------------------------------------------------------------

## A2 --- Secret Exfiltration

``` text
Researcher reads secret
  ->
secret taint
  ->
Executor receives derived data
  ->
external.post
  ->
BLOCK
```

Expected: - taint lineage - critical alert - quarantine

------------------------------------------------------------------------

## A3 --- Mission Drift

``` text
Mission:
Research Redis

Agent:
research
research
database.export
external.post
```

Expected: - drift detection - plan deviation - block

------------------------------------------------------------------------

## A4 --- Rogue Agent

``` text
Agent becomes malicious
  ->
requests forbidden tool
  ->
quarantine
  ->
reassign remaining task
  ->
other agents continue
```

This is the primary presentation demo.

------------------------------------------------------------------------

# 40. Demo Script

The final demo should be deterministic.

## Phase 1 --- Healthy

``` text
Planner       97
Researcher    95
Executor      96
```

Task:

``` text
"Research Redis caching and produce a report."
```

All actions allowed.

------------------------------------------------------------------------

## Phase 2 --- Attack

Researcher consumes malicious content.

It attempts:

``` text
database.export(customers)
```

------------------------------------------------------------------------

## Phase 3 --- Detection

Dashboard displays:

``` text
CRITICAL THREAT

Policy violation
Mission drift
Untrusted trigger
Sensitive data access
```

------------------------------------------------------------------------

## Phase 4 --- Containment

``` text
Researcher
95 -> 27

Status:
QUARANTINED
```

Planner and Executor remain active.

------------------------------------------------------------------------

## Phase 5 --- Evidence

Open incident.

Show:

``` text
source
 ->
researcher
 ->
database.export
 ->
blocked
```

------------------------------------------------------------------------

## Phase 6 --- Replay

Replay timeline.

------------------------------------------------------------------------

## Phase 7 --- Verification

Click:

``` text
VERIFY LEDGER
```

Show:

``` text
Hash chain       ✓
Signatures       ✓
Merkle proof     ✓
Blockchain       ✓
```

This is the complete end-to-end story.

------------------------------------------------------------------------

# 41. Team Structure --- Two Developers

Both developers push to `main`.

Because both are using the same branch, minimize simultaneous edits to
the same files.

## Developer 1 --- Core / Security

Own:

``` text
backend/app/
policies/
contracts/
agents/common/
agents/planner/
agents/researcher/
agents/executor/
ledger/
identity/
enforcement/
trust/
provenance/
drift/
anomaly/
```

Responsibilities:

-   event schema
-   agent identity
-   PEP
-   OPA
-   trust
-   enforcement
-   detectors
-   ledger
-   blockchain anchor
-   agent runtime

------------------------------------------------------------------------

## Developer 2 --- Product / UI / Demo

Own:

``` text
frontend/
attacks/
demos/
docs/
```

Responsibilities:

-   dashboard
-   live WebSocket UI
-   agent graph
-   incident view
-   replay UI
-   ledger verification UI
-   demo attack scripts
-   frontend integration
-   presentation/demo tooling

Developer 2 may modify backend API schemas when required, but should
coordinate before changing shared contracts.

------------------------------------------------------------------------

# 42. Shared Files

These require coordination:

``` text
ARCHITECTURE.md
README.md
docker-compose.yml
openapi/schema
backend/app/schemas/*
```

Before modifying a shared interface:

1.  Check current `main`.
2.  Make the smallest change possible.
3.  Tell the other developer.
4.  Commit immediately.
5.  Push.
6.  Other developer pulls before continuing.

------------------------------------------------------------------------

# 43. Git Rules

Both developers push directly to `main`.

### MUST

``` bash
git pull --rebase origin main
```

before starting work.

After completing a small logical unit:

``` bash
git add .
git commit -m "feat: ..."
git pull --rebase origin main
git push origin main
```

### NEVER

``` text
git push --force
```

### NEVER

Rewrite another developer's work.

### NEVER

Keep large uncommitted changes for hours.

### Prefer

Small commits:

``` text
feat: add agent registration
feat: add event signing
feat: add policy enforcement
feat: add trust engine
feat: add live agent dashboard
```

------------------------------------------------------------------------

# 44. Antigravity Coding Rules

Antigravity/AI coding agents must obey these rules.

## Rule 1 --- Read this file first

Before implementing anything:

``` text
ARCHITECTURE.md
```

is the source of truth.

------------------------------------------------------------------------

## Rule 2 --- No fake functionality

Do not:

``` python
return {"trust": 95}
```

unless that value is actually calculated.

Do not hardcode:

``` text
"Threat detected!"
```

The UI must consume real API data.

------------------------------------------------------------------------

## Rule 3 --- No mock security decisions

Security decisions must come from:

``` text
contract
+
policy
+
facts
+
risk
```

Demo attack scripts may generate deterministic inputs, but the security
engine must independently make the decision.

------------------------------------------------------------------------

## Rule 4 --- Default deny

Unknown:

``` text
agent
tool
path
command
domain
delegation
```

must not automatically receive permission.

------------------------------------------------------------------------

## Rule 5 --- Preserve interfaces

Implement against:

``` text
PolicyEngine
EventBus
Ledger
IdentityProvider
AnomalyModel
BlockchainAnchor
```

Do not tightly couple core logic to Redis, OPA, or a specific blockchain
SDK.

------------------------------------------------------------------------

## Rule 6 --- Tests before "done"

Every security feature must have at least:

``` text
1 positive test
1 negative test
```

Example:

``` text
allowed database read -> ALLOW
unauthorized database export -> DENY
```

------------------------------------------------------------------------

# 45. Implementation Order

Do not build everything in parallel.

## Phase 1 --- Foundation

``` text
Repository
Docker Compose
Postgres
Redis
FastAPI
Pydantic schemas
```

------------------------------------------------------------------------

## Phase 2 --- Identity + Events

``` text
Agent registration
Ed25519
Capability JWT
Event schema
Event signing
Hash chain
```

------------------------------------------------------------------------

## Phase 3 --- Enforcement

``` text
Mission contracts
OPA
PDP
PEP
Allow/deny
```

------------------------------------------------------------------------

## Phase 4 --- Trust

``` text
Trust engine
Trust tiers
Alerts
Enforcement controller
Quarantine
```

------------------------------------------------------------------------

## Phase 5 --- Agents

``` text
Planner
Researcher
Executor
```

Make the normal workflow work end-to-end.

------------------------------------------------------------------------

## Phase 6 --- Detection

``` text
Mission drift
Untrusted content
Taint
Behavior anomaly
```

------------------------------------------------------------------------

## Phase 7 --- Evidence

``` text
Merkle
Proof
Replay
Blockchain anchor
```

------------------------------------------------------------------------

## Phase 8 --- Dashboard

``` text
Live Ops
Agents
Alerts
Replay
Ledger
```

------------------------------------------------------------------------

## Phase 9 --- Attack Suite

``` text
Prompt injection
Secret exfiltration
Mission drift
Rogue agent
```

------------------------------------------------------------------------

## Phase 10 --- Polish

Only after the vertical slice works:

``` text
Animations
better graphs
better evidence panels
demo mode
metrics
presentation polish
```

------------------------------------------------------------------------

# 46. Definition of Done

The MVP is considered complete only when this scenario works without
manually editing the database:

``` text
1. Start Docker Compose.

2. Start AegisMesh.

3. Register Planner, Researcher and Executor.

4. Create a mission.

5. Planner generates a plan.

6. Researcher performs valid actions.

7. Valid actions are allowed.

8. Researcher consumes malicious content.

9. Researcher attempts forbidden sensitive action.

10. PEP intercepts it.

11. OPA/PDP evaluates it.

12. Action is denied.

13. Alert appears in dashboard.

14. Trust score decreases.

15. Researcher is quarantined.

16. Planner/Executor remain operational.

17. Taint/provenance is visible.

18. Event exists in signed ledger.

19. Merkle checkpoint is created.

20. Replay reconstructs the incident.

21. Ledger verification succeeds.

22. Blockchain anchor can be verified.

23. Attack test passes automatically.
```

If any of these are manually faked, the MVP is not complete.

------------------------------------------------------------------------

# 47. Success Metrics

Track:

``` text
decision latency p95
events/sec
blocked actions
allowed actions
alerts
false positives
quarantined agents
trust changes
ledger verification status
replay accuracy
attack detection rate
```

For the hackathon demo, prioritize correctness and explainability over
massive throughput.

------------------------------------------------------------------------

# 48. Product Positioning

Do not pitch AegisMesh as:

> "Another AI monitoring dashboard."

Pitch it as:

> **A runtime mission-integrity layer that sits between autonomous AI
> agents and the real world.**

The system answers:

``` text
WHO?
WHAT?
WHY?
ALLOWED?
CONSISTENT?
SAFE?
WHAT DATA?
WHAT HAPPENED?
CAN WE PROVE IT?
```

------------------------------------------------------------------------

# 49. Final Product Architecture

``` text
                         AEGISMESH
              Digital Immune System for AI
                              |
        ┌─────────────────────┼─────────────────────┐
        |                     |                     |
        v                     v                     v
   IDENTITY              MISSION              PROVENANCE
        |                     |                     |
        └──────────────┬──────┴──────┬──────────────┘
                       v
                RUNTIME INTERCEPTOR
                       |
              ┌────────┴────────┐
              v                 v
          POLICY             BEHAVIOR
          ENGINE             ENGINE
              |                 |
              └────────┬────────┘
                       v
                    RISK
                   ENGINE
                       |
          ┌────────────┼────────────┐
          v            v            v
       ALLOW       APPROVAL       BLOCK
                                     |
                                ┌────┴────┐
                                v         v
                             REVERT   QUARANTINE
                                |
                                v
                         EVIDENCE LEDGER
                                |
                   ┌────────────┼────────────┐
                   v            v            v
                REPLAY       MERKLE      BLOCKCHAIN
                   |            |            |
                   └────────────┴────────────┘
                                |
                                v
                           DASHBOARD
```

------------------------------------------------------------------------

# 50. The single most important implementation rule

**Do not build a collection of demos. Build one real security
pipeline.**

Everything should flow through:

``` text
ACTION
  ↓
IDENTITY
  ↓
CONTEXT
  ↓
MISSION
  ↓
PLAN
  ↓
PROVENANCE
  ↓
POLICY
  ↓
RISK
  ↓
DECISION
  ↓
ENFORCEMENT
  ↓
SIGNED EVIDENCE
  ↓
REPLAY
```

Once that pipeline is real, every additional feature becomes a detector
or interface plugged into it.

That is the architecture we should implement.
