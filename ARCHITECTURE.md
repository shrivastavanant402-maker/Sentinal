# SentinelMesh — Full Architecture
## PS002: Autonomous Agent Runtime Integrity System

> **Audience:** the team and AI coding agents (Antigravity/Gemini). This file is the single source of truth.
> If code and this file disagree, fix one of them **in the same commit**. Never diverge silently.
> Progress lives in `PROGRESS.md`. Interfaces between workstreams (schemas, API) live here and in `openapi.yaml`.

**Pitch:** SentinelMesh is a bodyguard for AI agents. It watches them, verifies them, catches hallucinations, stops rogue behavior, gives any single-agent IDE access to a full multi-agent team, and keeps a tamper-proof, replayable audit trail.

---

## 0. How to read this document

**Priority tags** (dependency order, not time estimates):

| Tag | Meaning |
|---|---|
| **P0** | PS002 core. Everything else depends on it. Build first. |
| **P1** | Differentiators promised in the submission: IDE Guard, hallucination detection, Agent Bridge, provenance, collusion, shadow simulation, forensic replay, Merkle ledger. |
| **P2** | Advanced backends from the tech stack that swap in behind an interface already built in P0/P1 (OPA alternatives, GNN, autoencoder, SPIRE, Kafka/NATS, JetBrains). Build the interface early, the swap last. |

**Design rule:** every component has a **default implementation** and, where the stack lists alternatives, a **pluggable interface** (`EventBus`, `PolicyEngine`, `AnomalyModel`, `IdentityProvider`, `VectorStore`). Code against the interface, never the vendor.

**Honesty rule (important for judges):** *Preventive* controls (SDK, MCP proxy, shell wrapper, LLM proxy) can stop an action before it happens. *Detective* controls (file watcher, git hooks) can only detect afterward and trigger revert. The docs, UI, and pitch must label each control as preventive or detective.

---

## 1. Goals and PS002 mapping

| PS002 requirement | Where it is built |
|---|---|
| Continuous monitoring of multi-agent execution | §7 Instrumentation, §5 Event bus |
| Real-time auditing | §5 Ledger, §18 Dashboard, WebSocket stream |
| Verify actions vs expected behavior | §8 Contracts, OPA policy, plan verifier |
| Catch drift, tampering, faulty behavior | §9 drift, attestation, integrity, anomaly |
| Identify behavioral anomalies | §9.1 anomaly ensemble |
| Identify policy violations | §8 policy, §9.4 taint |
| Flag or halt non-compliant agents | §11 enforcement controller |
| Trust and accountability | §6 identity, §10 trust, §5 ledger, §16 replay |

---

## 2. System architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│ IDE LAYER   VS Code │ Cursor │ Windsurf │ JetBrains │ Cline │ Continue │
│             (IDE Guard extension: diagnostics, sidebar, approvals)      │
└───────────────┬──────────────────────────────────────────────────────┘
                │ MCP / A2A / REST / OpenAI-compatible LLM proxy
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ SENTINELMESH AGENT BRIDGE (SMAB)                                       │
│ Discovery │ Router │ Negotiator │ Aggregator │ Trust Propagator │      │
│ Policy Adapter                                                         │
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ MONITORED MULTI-AGENT NETWORK                                          │
│ Planner │ Researcher │ Coder │ Tester │ Reviewer │ Security            │
│ (LangGraph default; AutoGen / CrewAI via SDK adapters)                 │
└───────────────┬──────────────────────────────────────────────────────┘
                │ every action passes a Policy Enforcement Point (PEP)
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ INSTRUMENTATION: Agent SDK (Py/TS) │ MCP proxy │ LLM proxy │          │
│ shell wrapper │ file watcher │ git hooks                              │
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ RUNTIME INTEGRITY CORE (PS002)                                         │
│ Identity │ Signed Event Bus │ Ledger (hash chain + Merkle) │           │
│ Policy Decision Point (facts → OPA) │ Plan Verifier │                  │
│ Detectors: anomaly, drift, taint, collusion, injection, hallucination │
│ Trust Engine │ Enforcement Controller │ Shadow Simulator │ Snapshots  │
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ OUTPUT: Dashboard (8 views) │ IDE diagnostics │ Alerts │ Forensic      │
│ Replay │ Grafana/Jaeger │ CLI                                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Three planes:**
- **Data plane:** agents, tools, PEPs. Latency-sensitive.
- **Control plane:** PDP, OPA, trust, enforcement. Decides.
- **Evidence plane:** ledger, replay, dashboard. Proves.

---

## 3. Tech stack (final)

| Layer | Default | Pluggable / advanced (P2) |
|---|---|---|
| Agent frameworks | LangGraph | AutoGen, CrewAI (via SDK adapters) |
| Backend | Python 3.11, FastAPI, Uvicorn, Pydantic v2 | Go or Rust sidecar for the PEP hot path |
| Event bus | Redis Streams | NATS JetStream, Kafka |
| Policy engine | OPA (Rego), run as a sidecar container | Cedar |
| Primary store | PostgreSQL | TimescaleDB extension for event time-series |
| Analytics | Postgres/Timescale | ClickHouse |
| Cache / revocation / rate limits | Redis | |
| Vector store | Qdrant | Weaviate |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2, local) | Gemini/OpenAI embeddings |
| ML | scikit-learn (Isolation Forest), River (online) | PyTorch autoencoder |
| Graph | NetworkX | PyTorch Geometric (GNN) |
| Static analysis | Semgrep, Bandit, tree-sitter | CodeQL |
| Type/symbol checks | pyright, tsc, language servers via LSP | rust-analyzer |
| Identity | Ed25519 signing, did:key, capability JWT (EdDSA), internal mTLS (step-ca) | SPIFFE/SPIRE |
| Observability | OpenTelemetry, Prometheus, Grafana, Jaeger | |
| Frontend | Next.js, React, Tailwind, shadcn/ui | |
| Graph viz | React Flow (or Cytoscape.js) | |
| Real-time | WebSocket | |
| IDE | VS Code Extension API (TypeScript) | JetBrains Plugin SDK (Kotlin) |
| Sandbox | Docker (`--network none`, read-only rootfs, tmpfs) | gVisor/Firecracker |
| Deployment | Docker Compose | Kubernetes (Helm chart) |

**LLM note:** agents in `llm` mode need a model API key (for example a Gemini API key). IDE subscription credits that power Antigravity do not cover your app's runtime API calls. Every demo and attack also has a deterministic `scripted` mode that needs no key.

---

## 4. Repository structure

```text
sentinelmesh/
├── ARCHITECTURE.md
├── PROGRESS.md
├── openapi.yaml                   # generated from FastAPI; source for TS/Kotlin clients
├── Makefile                       # run, test, attack, benchmark, lint, gen-clients
├── docker-compose.yml
├── core/
│   ├── schemas/                   # Pydantic models: Event, Decision, Alert, Finding, Contract, Plan
│   ├── event_bus/                 # EventBus interface + redis_streams.py (+ nats.py, kafka.py)
│   ├── identity/                  # keys, did:key, registry, attestation, capability tokens, mTLS helpers
│   ├── ledger/                    # hash chain, Merkle checkpoints, proofs, verify, external anchor
│   ├── contracts/                 # YAML loader, validator, compiler → OPA data
│   ├── policy/                    # PolicyEngine interface + opa_client.py; rego/ lives in /policies
│   ├── pdp/                       # decision pipeline: facts → policy → obligations → decision
│   ├── verifier/                  # plan verifier (state machine)
│   ├── detectors/
│   │   ├── anomaly/               # ewma.py, isolation_forest.py, autoencoder.py (P2)
│   │   ├── drift/                 # semantic drift (embeddings + Qdrant)
│   │   ├── provenance/            # taint + untrusted-content provenance
│   │   ├── collusion/             # motifs.py, gnn.py (P2)
│   │   ├── injection/             # heuristics + classifier
│   │   └── hallucination/         # packages, apis, files, tests, security, claims
│   ├── trust/                     # trust engine + propagation
│   ├── enforcement/               # controller, approvals, throttle, halt, quarantine
│   ├── shadow/                    # shadow simulator (digital twin)
│   ├── snapshots/                 # pre-action snapshots + revert
│   ├── replay/                    # session reconstruction + deterministic policy re-evaluation
│   ├── api/                       # FastAPI routers + WebSocket hub
│   └── telemetry/                 # OpenTelemetry + Prometheus metrics
├── bridge/                        # Agent Bridge (SMAB)
│   ├── discovery/ router/ negotiator/ aggregator/ trust_propagator/ policy_adapter/
│   ├── protocols/{mcp,a2a,rest,llm_proxy}/
│   └── network/                   # native agents: planner, researcher, coder, tester, reviewer, security
├── instrumentation/
│   ├── sdk_python/                # guard(), signing, adapters for LangGraph/AutoGen/CrewAI
│   ├── sdk_ts/
│   ├── mcp_proxy/
│   ├── llm_proxy/
│   ├── shell_wrapper/             # sm-shell
│   ├── watchers/                  # file watcher
│   └── git_hooks/
├── ide/
│   ├── vscode/                    # TypeScript extension
│   ├── jetbrains/                 # Kotlin plugin (P2)
│   └── shared/                    # generated API clients, claim-vs-reality model
├── dashboard/
│   ├── frontend/                  # Next.js app (8 views)
│   └── backend/                   # BFF/aggregation endpoints if needed
├── policies/                      # Rego policies + tests (opa test)
├── contracts/                     # per-agent YAML contracts
├── ml/                            # training scripts, synthetic data generators, saved models
├── demos/
│   ├── multi_agent_attack/
│   ├── ide_hallucination/
│   ├── collusion/
│   └── bridge_delegation/
├── attacks/                       # attack scripts + benign scenarios (the acceptance suite)
├── benchmark/                     # harness, labelled scenarios, result writer
├── tests/                         # unit, integration, e2e
├── scripts/seed_events.py         # dev-only: real-schema events through real endpoints
├── docs/
└── deploy/                        # compose files, helm chart, grafana dashboards, otel config
```

---

## 5. Events, bus and ledger (P0)

### 5.1 Event schema (canonical)

```json
{
  "id": "uuid4",
  "seq": 1284,
  "ts": "2026-10-03T10:15:22.123Z",
  "trace_id": "otel trace id",
  "span_id": "otel span id",
  "parent_event_id": "uuid or null",
  "agent_id": "coder",
  "session_id": "sess-001",
  "source": "sdk|mcp_proxy|llm_proxy|shell|fs_watcher|git_hook|ide|core",
  "type": "tool_call_request",
  "payload": { "tool": "fs.write", "args": { "path": "src/cache.py" } },
  "labels": ["untrusted", "secret"],
  "policy_version": "sha256 of policy bundle used",
  "decision": null,
  "content_hash": "hex",
  "prev_hash": "hex",
  "hash": "hex",
  "agent_signature": "base64",
  "signature": "base64"
}
```

**Event types:**
`agent_registered`, `heartbeat`, `attestation`, `plan_declared`, `plan_step`, `tool_call_request`, `decision`, `tool_call_result`, `llm_prompt`, `llm_response`, `message`, `delegation`, `fs_change`, `git_event`, `claim`, `finding`, `alert`, `enforcement`, `trust_update`, `approval_requested`, `approval_resolved`, `simulation_result`, `snapshot`, `revert`, `bridge_task`, `bridge_delegation`, `bridge_result`, `ide_session`, `checkpoint`.

### 5.2 Hashing and signing (definitive)

1. The producer builds the event without `seq`, `prev_hash`, `hash`, `agent_signature`, `signature`.
2. `content_hash = sha256(canonical_json(event_without_those_fields))`. Canonical JSON: sorted keys, no whitespace, UTF-8.
3. **Agent-originated events:** the agent signs `content_hash` with its Ed25519 key, producing `agent_signature`.
4. The ledger (single writer) assigns `seq` and `prev_hash`, then computes `hash = sha256(content_hash || prev_hash || seq)`.
5. The core signs `hash` with the core key, producing `signature`. **System events** (decision, alert, enforcement, trust_update, approvals, checkpoint) have no `agent_signature`.
6. Verification checks both signatures, the hash recomputation, and chain continuity.

### 5.3 Ledger: hash chain plus Merkle checkpoints

- **Single writer** (the ledger service) appends events inside a transaction using a Postgres advisory lock. Producers publish to the bus, the ledger consumes in order, assigns seq, and stores. Inline enforcement uses a synchronous path that calls the same append function.
- **Merkle checkpoints:** every 100 events or 30 s, whichever first, compute the Merkle root over event `hash` values in the range. Append a `checkpoint` event `{from_seq, to_seq, merkle_root}` signed by the core.
- **External anchor:** each checkpoint root is also appended to `anchors/anchors.log` (append-only file) and optionally committed and pushed to a git remote. This catches the case where an attacker rewrites the entire database consistently.
- **Inclusion proof:** `GET /v1/ledger/proof/{seq}` returns the Merkle path so any single event can be proven part of a signed checkpoint.
- **Verify** (`GET /v1/ledger/verify`): (1) recompute hashes and chain, (2) verify all signatures against the registry, (3) recompute Merkle roots against checkpoints, (4) compare checkpoints with the external anchor log. Return `{ok, checked, first_broken_seq, reason, checks: {chain, signatures, merkle, anchor}}`.

### 5.4 Event bus

`EventBus` interface: `publish(topic, event)`, `subscribe(topic, group)`. Default: Redis Streams with consumer groups. Topics: `events.raw`, `events.ledgered`, `alerts`, `enforcement`. Detectors consume `events.ledgered`; the WebSocket hub consumes everything.

### 5.5 Data model (Postgres)

`events`, `agents`, `agent_attestations`, `contracts` (versioned), `policy_bundles` (versioned, hash), `sessions`, `alerts`, `findings`, `trust_history`, `approvals`, `snapshots`, `taint_registry`, `bridge_tasks`, `checkpoints`, `ide_sessions`. The `events` table is append-only (revoke UPDATE/DELETE from the app role; the tamper demo uses a superuser role).

---

## 6. Identity and attestation (P0, advanced backends P2)

- **Agent identity:** each agent generates an Ed25519 keypair at start. The public key is registered; the agent DID is `did:key` derived from it. A SPIFFE-style ID `spiffe://sentinelmesh.local/agent/<id>` is stored in the registry and in capability tokens (real SPIRE issuance is a P2 backend).
- **Registry:** `agent_id`, role, public key, DID, contract version, status (`active|watched|restricted|halted|quarantined`), trust, last heartbeat.
- **Attestation (tamper detection for the agent itself):** on registration and every heartbeat the agent sends `{code_hash, framework, version, launch_args_hash}` signed with its key. `code_hash` is the sha256 of the agent's source files or container image digest. A change mid-run emits `attestation_drift` (critical).
- **Capability tokens:** short-lived JWT (EdDSA, ~5 min) with `sub`, `session`, allowed tool scopes, `jti`. Refreshed via heartbeat. Revoked by adding `jti` to the Redis revocation set. **Halting an agent = revoking its token plus setting status.**
- **Service-to-service:** mTLS using a local CA (step-ca) between core, OPA, bridge, and proxies. P2: replace the CA with SPIRE.
- **Human auth:** dashboard and IDE use a JWT login (single-user or simple RBAC: viewer, operator, admin). Approvals and halts require operator or higher and are themselves ledgered.

---

## 7. Instrumentation (P0 SDK and MCP proxy, P1 the rest)

Each wrapper is a **PEP**: it builds a signed event, asks the PDP, and acts on the decision. All emit events with a `source` field.

| Wrapper | Type | What it does |
|---|---|---|
| **Agent SDK (Python, TS)** | Preventive | `guard.call(tool, args)` signs and sends `tool_call_request`, executes only on `allow`, posts `tool_call_result`. Raises `ActionDenied`, `AgentHalted`, `ApprovalTimeout`. Adapters wrap LangGraph tools, AutoGen functions, CrewAI tools. Also emits `plan_declared`, `message`, `delegation`, `heartbeat`. |
| **MCP proxy** | Preventive | Sits between an MCP client (IDE agent) and real MCP servers (stdio and HTTP/SSE). Intercepts `tools/call`, asks the PDP, forwards on allow, returns a JSON-RPC error with the reason on deny. Also logs `tools/list` and resource reads. |
| **LLM proxy** | Preventive (prompts), detective (responses) | OpenAI-compatible reverse proxy (plus Gemini and Anthropic-style endpoints). IDE agents that allow a custom base URL point at it. Logs `llm_prompt` and `llm_response` (stores hashes by default, content encrypted when `LOG_CONTENT=true`). Prompt side: secret/PII scan (DLP) with redaction or block. Response side: injection indicators, proposed tool calls forwarded to the PDP for pre-check. |
| **Shell wrapper (`sm-shell`)** | Preventive | A shim shell or PTY wrapper that sends each command to the PDP before executing. Used as the agent's terminal. Supports allow/deny/approval and `simulate_first` (see §12). |
| **File watcher** | **Detective** | `watchdog` over the workspace. Emits `fs_change` with before/after hash and diff stats. Attributes to an agent by time window plus process. Protected-path writes (for example `.env`) trigger alert plus revert from snapshot. Cannot prevent writes by agents that bypass the PEPs, and the UI must say so. |
| **Git hooks** | **Detective / gate** | `pre-commit`, `pre-push`, `post-commit`. Verify the diff: hallucination checks, secret scan, claim verification. A critical finding blocks the commit. |

**Contract for all PEPs:** fail-closed for P0 high-risk tools (PDP unreachable → deny), fail-open with loud alert for low-risk reads, configurable per tool risk level.

---

## 8. Verification: contracts, policy, plan verifier (P0)

### 8.1 Behavioral contracts (YAML, one per agent)

```yaml
agent_id: coder
role: "Writes and edits source code for assigned tasks"
version: 3
allowed_tools: [fs.read, fs.write, shell.exec, git.diff]
fs:
  read_allow:   ["workspace/**"]
  write_allow:  ["workspace/src/**", "workspace/tests/**"]
  deny:         ["**/.env", "**/*.pem", "**/id_rsa*"]
shell:
  allow_commands: ["pytest", "npm test", "pip install", "ls", "cat"]
  deny_patterns:  ["curl .*\\|\\s*sh", "rm -rf /", "chmod 777"]
http:
  domain_allow: ["pypi.org", "registry.npmjs.org"]
rate_limit: { max_calls_per_10s: 20 }
may_receive_delegation_from: [planner]
risk_levels: { fs.read: low, fs.write: medium, shell.exec: high, http.get: medium }
obligations:
  shell.exec: [simulate_first]
  fs.write:   [snapshot_before]
```

Contracts are validated against a JSON Schema, versioned, hashed, and compiled to JSON as OPA **data**. Default deny: unknown tool, path, command, or domain is denied.

### 8.2 Policy decision point (PDP) pipeline

```text
event → 1 integrity (signatures, chain input, replay id, token valid, attestation ok)
      → 2 agent status (halted / quarantined → deny)
      → 3 facts: contract match, rate, taint hits, delegation intersection,
                 plan conformance, untrusted-provenance, injection score, trust tier
      → 4 OPA (Rego) evaluates facts + contract data → decision + severity + obligations
      → 5 obligations executor: snapshot_before | simulate_first | require_approval | notify
      → 6 decision event appended to ledger, published, returned to PEP
```

**OPA input:**
```json
{ "event": {...},
  "agent": {"id": "coder", "role": "...", "trust": 82, "tier": "trusted", "status": "active"},
  "session": {"plan_state": "implementing", "delegation_chain": ["planner","coder"],
              "taint_labels": ["secret:.env"]},
  "facts": {"contract_ok": true, "rate_ok": true, "taint_hit": false,
            "delegation_ok": true, "plan_ok": true, "untrusted_trigger": false,
            "injection_score": 0.12},
  "context": {"now": "...", "recent_rate": 4} }
```
**OPA output:** `{decision, reason_code, reason, severity, obligations[]}`. Every decision stores the `policy_version` hash so replay can re-evaluate with the exact policy (§16). Rego policies live in `/policies` with `opa test` unit tests. Cedar can implement the same `PolicyEngine` interface (P2).

### 8.3 Plan verifier (state machine)

The Planner (or the Bridge on behalf of the IDE) emits `plan_declared`:
```json
{ "goal": "Add Redis caching with tests and security review",
  "steps": [
    {"id": "s1", "agent": "researcher", "tools": ["http.get", "fs.read"], "next": ["s2"]},
    {"id": "s2", "agent": "coder",      "tools": ["fs.write", "shell.exec"], "next": ["s3"]},
    {"id": "s3", "agent": "tester",     "tools": ["shell.exec"], "next": ["s4"]},
    {"id": "s4", "agent": "reviewer",   "tools": ["fs.read"], "next": ["s5"]},
    {"id": "s5", "agent": "security",   "tools": ["fs.read", "shell.exec"], "next": []} ] }
```
The verifier tracks the current state per session. An action by an agent or tool not enabled in the current state is a **plan deviation**: `plan_ok=false` as a PDP fact (low/medium alert, escalates if repeated). Skipped mandatory steps (for example Security review before final result) are flagged at completion.

---

## 9. Detectors

Inline detectors compute PDP facts synchronously (<100 ms). Async detectors consume the ledgered stream and may emit alerts that the enforcement controller escalates.

### 9.1 Anomaly detection (async, P0 EWMA, P1 Isolation Forest, P2 autoencoder)

- **Features per agent per window (10 s):** calls, distinct tools, mean arg length, arg entropy, path depth, inter-arrival time, error/deny rate, bytes out, first-seen tool/path/domain flags.
- **EWMA + z-score** per feature (z > 3 → medium).
- **Isolation Forest** (scikit-learn; online alternative: River HalfSpaceTrees) trained on benign runs from the benchmark generator, retrained on a schedule.
- **Autoencoder** (PyTorch) over feature windows; reconstruction error above a calibrated threshold → anomaly.
- **Ensemble score** = weighted max; each model reports its contribution in the alert for explainability.
- `AnomalyModel` interface so models plug in without changing the pipeline.

### 9.2 Semantic drift (async, P1)

- Embed the session **goal** and each agent's rolling window of actions/messages (local sentence-transformers).
- Store per-agent baseline embeddings and the goal vector in Qdrant.
- **Drift score** = max(distance from goal, distance from agent baseline centroid). Above threshold for N consecutive windows → drift alert (medium, then high).
- Cheap pre-filter: skip embedding when the action is exactly in the plan's expected tool set.

### 9.3 Injection and instruction provenance (inline + async, P1)

- **Untrusted content labeling:** anything from external or retrieved sources (web pages, documents, tool outputs from third parties, retrieved memory) is labeled `untrusted`.
- **Heuristic + classifier scoring** of untrusted content for instruction-like text ("ignore previous", role-change, exfil phrasing); an LLM-judge fallback runs async.
- **Provenance rule:** a high-risk action requested right after the agent consumed high-scoring untrusted content gets `untrusted_trigger=true`. Policy can require approval or deny.
- **Memory poisoning:** agent memory writes inherit the labels of their source; later reads re-introduce the label.

### 9.4 Provenance and taint tracking (inline, P1)

- **Sources:** files matching deny/secret patterns, `.env` values, results from tools tagged `sensitivity: secret|pii`, regex/entropy scanners for keys, tokens, emails, phone and ID numbers.
- **Registration:** each source value is stored by fingerprint (sha256 of normalized tokens ≥ 8 chars, plus fuzzy n-gram sketches for partial leaks) with `origin_agent`, `origin_event`, label.
- **Propagation:** taint attaches to the **session** and to messages/results derived from tainted inputs (conservative: any message produced by an agent after reading tainted data and containing a fingerprint match is tainted; LLM-rewritten leaks are caught by the n-gram sketch plus the async semantic check).
- **Sinks:** `http.post`, `http.get` to non-allowlisted domains (query strings), `shell.exec`, `fs.write` outside allowed paths, `git.push`, outbound `message` to agents not cleared for the label, LLM prompts to external models.
- **Violation:** tainted fingerprint in sink args → `taint_hit=true` → deny, critical, halt origin chain.
- **Lineage view:** the dashboard renders the taint path source → agent → agent → sink.

### 9.5 Collusion detection (async, P1 motifs, P2 GNN)

NetworkX `DiGraph` per session; nodes are agents, edges are `message`, `delegation`, `data-flow` (taint carriers) with counts and timestamps.

**Motifs:**
- Ping-pong cycles (A→B→A repeated > N times in a window)
- Relay chains moving labeled data across ≥ 2 hops toward a sink
- Mutual approval (A approves B's request while B approves A's)
- Delegation widening (delegate acts beyond the delegator's permissions)
- Star amplification (one agent fan-out to many in bursts)
- Synchronized bursts across agents

**GNN (P2):** PyTorch Geometric GraphSAGE node classifier trained on synthetic session graphs (benign versus collusive) from `ml/`. Runs async; motif detector remains the fallback and the explanation source.

### 9.6 Hallucination and claim verification (P1)

Applies to IDE-agent and network-agent outputs. Pipeline:

1. **Claim extraction:** parse agent final messages and plan steps into structured `claim` events: `installed(pkg)`, `created(file)`, `modified(file)`, `tests_passed(n)`, `uses_api(symbol)`, `fixed(issue)`, `no_secrets`.
2. **Checks** (each emits a `finding` with `severity`, `evidence`, `confidence`):

| Check | How |
|---|---|
| **Fake packages** | Query PyPI, npm, crates.io JSON APIs. Not found → critical (possible slopsquatting). Also: very new/low-download package, edit-distance typosquat of a popular package, name not in lockfile. Results cached. |
| **Fake APIs / symbols** | tree-sitter parse the diff for imports, calls, attributes. Resolve against the repo index, installed package introspection, and LSP (`pyright`, `tsc`, `rust-analyzer`). Unresolved symbol or wrong signature → finding. |
| **Fake file references** | Parse paths in code and messages; verify against the repo tree (and git index). |
| **False test claims** | Actually run the tests in the sandbox (§12). Compare real pass/fail counts with the claim. Mismatch → high. |
| **Insecure code** | Semgrep (OWASP rules) and Bandit on changed files; CodeQL optional. Hardcoded secrets, SQL injection, unsafe deserialization, shell injection → finding. |
| **Unsupported claims** | RAG over the repo (Qdrant). For each factual claim about the codebase, retrieve evidence and run an entailment check (NLI model or LLM judge). No supporting evidence → low/medium. |

3. **Claim-vs-reality record:** `{claim, verdict: verified|contradicted|unverifiable, evidence}` feeds the IDE sidebar and the trust engine (false claims reduce claim-accuracy trust).
4. **Triggers:** on `fs_change` and `git_event` (watcher/hooks), on `claim` events, and before the Bridge returns results to the IDE.

---

## 10. Trust engine (P0)

**Dimensions per agent (0–100):** `compliance` (policy), `integrity` (signatures/attestation), `consistency` (anomaly/drift), `claim_accuracy` (hallucination findings).

`trust = clamp(0.35*compliance + 0.25*integrity + 0.2*consistency + 0.2*claim_accuracy)` (weights configurable). Start all dimensions at 100.

**Penalties** by alert severity on the relevant dimension: low −5, medium −15, high −30, critical −50. **Recovery:** +1 per 10 consecutive clean allowed actions, capped at 100. Every change emits a `trust_update` with dimension and reason.

**Trust to autonomy (tiers):**

| Trust | Tier | Effect |
|---|---|---|
| ≥ 80 | trusted | Normal |
| 60–79 | watched | Throttled rate limit, alerts flagged in IDE |
| 40–59 | restricted | `risk >= medium` tools need approval; shadow simulation forced for `shell.exec` |
| < 40 | quarantined | Halted and isolated; operator must release |

**Trust propagation (Bridge):** the trust of a delegated result = `min(trust of agents in the chain) × verification_factor`, where `verification_factor` drops when claim checks contradict the result. Shown per result in the IDE.

---

## 11. Enforcement controller (P0 core, P1 sandbox/revert)

**Graduated ladder** (each step is a ledgered `enforcement` event):

```text
Log → Flag → Throttle → Require Approval → Sandbox → Revert → Halt → Quarantine
```

| Step | Mechanism |
|---|---|
| **Log** | Ledger only |
| **Flag** | Alert in dashboard, IDE diagnostic, notification |
| **Throttle** | Redis token bucket; lowers the agent's rate limit |
| **Require approval** | Creates `approval_requested`; PEP blocks until `approval_resolved` (dashboard or IDE). 60 s timeout → deny |
| **Sandbox** | Action is redirected to the Shadow Simulator (§12); result decides allow/deny |
| **Revert** | Restore the latest snapshot for the affected paths (§12.3); emits `revert` |
| **Halt** | `status=halted`, capability token revoked, in-flight approvals denied; SDK raises `AgentHalted` |
| **Quarantine** | Halt plus isolation: all tools removed from the contract, network denied, session frozen, artifacts labeled, human release required |

**Automatic escalation rules** (configurable): critical taint or integrity violation → halt immediately; 3 high alerts in 5 min → quarantine; trust tier transitions apply the tier effects above.
**Human overrides:** approve, deny, halt, resume, release quarantine, edit contract (new version), all ledgered with the operator identity.

---

## 12. Shadow simulation, snapshots and revert (P1)

### 12.1 Shadow simulator (digital twin)

Triggered by the obligation `simulate_first`, the trust tier, or an explicit policy rule.
- **Filesystem:** copy-on-write overlay (or a temp copy of the workspace) mounted into the sandbox.
- **Shell:** run the command in a throwaway Docker container (`--network none`, read-only rootfs apart from the overlay, CPU/memory/time limits, dropped capabilities).
- **Network:** requests go to a recorder/mock that logs the attempted calls instead of sending them.
- **Result:** `simulation_result` with `{fs_diff, deleted_paths, network_attempts, processes, exit_code, risk_score}`.
- **Risk evaluator:** rules plus policy (mass deletes, writes to protected paths, outbound calls to non-allowlisted hosts, privilege changes, `curl | sh`). Verdict `safe` → re-execute for real. `unsafe` → deny and alert.
- Limits to document: the twin covers filesystem and shell effects; it does not cover side effects in external services.

### 12.2 Test and verification sandbox

The same sandbox runs the project's tests for the false-test-claim check (§9.6).

### 12.3 Snapshots and revert

Obligation `snapshot_before`: before risky writes, take a snapshot (git stash/commit ref for repos; tar or hardlink copy for non-git paths). Stored in `snapshots` with the event id. `POST /v1/snapshots/{id}/revert` restores the paths and emits `revert`. The file watcher uses the same mechanism to roll back protected-path edits it detects.

---

## 13. Agent Bridge — SMAB (P1)

Purpose: **any single-agent IDE connects and gets a full, monitored multi-agent team.**

### 13.1 Components

| Component | Responsibility |
|---|---|
| **Discovery** | Registry of available agents with capabilities, cost, current trust, load. Publishes A2A-style agent cards at `/.well-known/agent.json`. |
| **Router** | Maps a task to a pipeline (a plan) from templates plus Planner output. |
| **Negotiator** | Matches required capabilities to agents by capability fit, trust, load, and cost. Excludes agents with tier below the task's required tier. May re-negotiate if an agent is halted. |
| **Aggregator** | Collects step outputs, resolves conflicts (for example Reviewer vs Coder), runs verification (hallucination checks, tests, security scan) before returning, produces the final result plus a summary of what each agent did. |
| **Trust Propagator** | Computes result trust across the chain (§10) and attaches it to the response. |
| **Policy Adapter** | Maps the IDE-side permissions (workspace root, allowed paths, user-approved actions) into contracts for delegated agents, so a delegated agent never has more authority than the user's IDE session. Effective permissions = intersection. |

### 13.2 Protocols

- **MCP server** (primary for IDEs). Tools: `delegate_task(task, constraints)`, `get_task_status(task_id)`, `get_trace(task_id)`, `list_agents()`, `cancel_task(task_id)`, `approve(approval_id, decision)`. Streams progress notifications.
- **A2A:** agent card endpoint plus task submission for agent-to-agent clients.
- **REST/WebSocket:** same operations for custom clients and the dashboard.
- **LLM proxy:** for IDE agents without MCP support but with a custom base URL (§7).

### 13.3 Delegation flow

```text
1  IDE agent (Cursor/Cline) calls MCP tool delegate_task("Add Redis caching with tests and security review")
2  Bridge opens ide_session, binds workspace and permissions (Policy Adapter)
3  Router → Planner agent produces plan_declared (§8.3)
4  Negotiator assigns Researcher, Coder, Tester, Reviewer, Security by capability/trust
5  Each agent runs through the SDK PEP: every action is checked, logged, signed
6  Hallucination checks run on Coder output (packages, APIs, tests actually run, Semgrep)
7  Violation mid-flow → controller halts the rogue agent, Negotiator reassigns the step
8  Aggregator verifies and merges, Trust Propagator scores the result
9  Result + diff + agents used + trust scores + trace id stream back to the IDE
10 Replay of the whole cross-boundary trace is available from the dashboard
```

### 13.4 Native agent network

Planner, Researcher, Coder, Tester, Reviewer, Security. Each has a contract in `/contracts`, an Ed25519 identity, and LangGraph implementation (`bridge/network/`). Tools are real (workspace file ops, test runner, Semgrep) and routed through the PEP. A `scripted` mode replays deterministic behaviors for attacks and tests.

---

## 14. IDE Guard (P1 VS Code, P2 JetBrains)

**Architecture:** the extension is a thin client of the Dashboard API (generated TypeScript client from `openapi.yaml`) over REST and WebSocket. It does not reimplement detection. It also registers the workspace with a `ide_session`.

**Features:**
- **Inline diagnostics:** 🟡 warnings / 🔴 errors on lines flagged by findings (fake package in `requirements.txt`, unresolved symbol, insecure pattern), via the VS Code Diagnostics API with code actions ("Replace with real package", "Show evidence", "Approve", "Revert change").
- **Sidebar (webview):** agent list with trust scores and tier, live timeline, alerts, pending approvals, claim-vs-reality table, delegated-task status (from the Bridge).
- **Status bar:** overall guard state and worst current trust.
- **Notifications:** approval requests with Approve/Deny buttons.
- **Commands:** halt agent, resume, revert last change, open replay in browser, verify ledger.
- **Setup helper:** writes the MCP proxy and LLM proxy config for Cursor, Cline, Continue, and Windsurf, and installs git hooks.

**JetBrains (P2):** Kotlin plugin with `ExternalAnnotator` for diagnostics, a tool window for the sidebar, notifications for approvals, using a Kotlin client generated from `openapi.yaml`. Feature parity with the VS Code extension except webview polish.

---

## 15. Observability (P1)

- OpenTelemetry traces: each session is a trace; each event carries `trace_id`/`span_id`; delegation creates child spans, so Jaeger shows the cross-boundary trace.
- Prometheus metrics: events/s, decision latency histogram, decisions by outcome, alerts by severity, trust by agent, detector latencies, ledger lag, bus lag.
- Grafana dashboards in `deploy/grafana/` for operations (separate from the product dashboard).

---

## 16. Forensic replay (P1)

- `GET /v1/sessions/{id}/replay` returns ordered events plus reconstructed state at each step (agent statuses, trust, plan state, taint labels, pending approvals).
- **Deterministic re-evaluation:** the replayer re-runs the PDP over recorded inputs using the `policy_version` stored with each decision and compares to the recorded decision. Any mismatch is reported. **Replay accuracy = matches / total decisions** (target 100%).
- UI: timeline scrubber, play/pause/speed, jump to alerts, step detail (inputs, facts, policy decision, evidence), taint lineage overlay, agent graph evolution, ledger proof button for any event.

---

## 17. API contract

All JSON, base path `/v1`, auth via JWT (humans) or capability token / signed events (agents). `openapi.yaml` is generated and drives TS and Kotlin clients.

**Agents and identity**

| Method | Path | Purpose |
|---|---|---|
| POST | `/agents/register` | public key + attestation → registration + token |
| POST | `/agents/{id}/heartbeat` | attestation refresh, token refresh |
| GET | `/agents`, `/agents/{id}` | list/detail incl. trust dimensions, tier, contract |
| POST | `/agents/{id}/halt`, `/resume`, `/release` | operator actions |

**Enforcement path**

| POST | `/enforce` | signed `tool_call_request` → Decision |
|---|---|---|
| POST | `/events` | signed non-decision events |
| POST | `/llm/check` | pre-check of proposed LLM prompt/response (used by LLM proxy) |
| GET | `/approvals`, POST `/approvals/{id}/decision` | approvals |

**Evidence**

| GET | `/events` | `since_seq`, `agent_id`, `session_id`, `type`, `source`, `limit` |
| GET | `/alerts`, `/findings` | filters: severity, agent, type |
| GET | `/ledger/verify`, `/ledger/proof/{seq}`, `/ledger/checkpoints` | integrity |
| GET | `/sessions`, `/sessions/{id}`, `/sessions/{id}/replay`, `/sessions/{id}/graph`, `/sessions/{id}/taint` | forensics |

**Policy and contracts**

| GET/PUT | `/contracts/{agent_id}` | versioned contracts |
| GET/POST | `/policies` | list bundles, upload and activate (runs `opa test` first) |
| POST | `/policies/simulate` | dry-run a policy change against recorded events |

**Bridge, IDE, shadow, snapshots**

| POST | `/bridge/tasks` | create task (REST equivalent of `delegate_task`) |
| GET | `/bridge/tasks/{id}`, `/bridge/tasks/{id}/trace` | status, trace |
| GET | `/bridge/agents` | discovery |
| POST | `/ide/sessions` | register IDE workspace |
| GET | `/ide/sessions/{id}/diagnostics` | findings mapped to file/line |
| GET | `/ide/sessions/{id}/claims` | claim-vs-reality |
| POST | `/shadow/simulate` | simulate an action |
| GET | `/snapshots`, POST `/snapshots/{id}/revert` | snapshots/revert |

**Ops**

| GET | `/metrics` | KPIs for the dashboard |
| GET | `/healthz` | health |
| POST | `/admin/reset` | demo reset |

**WebSocket** `/ws/stream`: `{ "kind": "event|alert|finding|trust|agent_status|approval|bridge|checkpoint", "data": {...} }`; client may send `{ "subscribe": [...], "agent_id": "...", "session_id": "..." }`.

---

## 18. Dashboard (8 views, P0 views 1–3 and 5, P1 the rest)

Dark mode first. Next.js + React + Tailwind + shadcn/ui, 3-column layout (nav | main | detail), live over WebSocket. **Color = trust:** green > 80, yellow 60–80, orange 40–60, red < 40. Every number comes from the API; no mocks outside `scripts/seed_events.py`.

| View | Contents | Data |
|---|---|---|
| **1. Live Ops** | KPI strip (events/s, blocked, alerts, decision latency p95, ledger status), agent graph (React Flow, nodes colored by trust, edges = messages/delegations/data-flow), live timeline, alert stream | `/metrics`, `/ws/stream`, `/sessions/{id}/graph` |
| **2. Agents** | Table plus drill-down: trust dimensions chart, tier, contract viewer, violations, Halt/Resume/Release buttons, attestation status | `/agents`, `/agents/{id}` |
| **3. Alerts** | Incident queue, severity filters, evidence panel (event, facts, policy reason, taint lineage), inline actions (approve, deny, halt, revert, acknowledge) | `/alerts`, `/approvals` |
| **4. Replay** | Forensic player: scrubber, speed, graph evolution, step detail, replay accuracy score | `/sessions/{id}/replay` |
| **5. Audit Ledger** | Event chain browser, Merkle checkpoints, inclusion proof viewer, **Verify** button with per-check results (chain, signatures, Merkle, anchor) | `/ledger/*` |
| **6. IDE Guard** | Developer view: findings by file with evidence, claim-vs-reality table, package checks, test-claim results, security findings | `/ide/sessions/*`, `/findings` |
| **7. Bridge** | Delegated task list, pipeline view (Planner → … → Security), per-agent status/trust, result trust, reassignments, cross-boundary trace link (Jaeger) | `/bridge/*` |
| **8. Policies** | Contract editor (YAML with schema validation), Rego bundle viewer, policy simulation against recorded events, version history | `/contracts/*`, `/policies/*` |

---

## 19. Deployment

**Docker Compose services:** `core-api`, `ledger-writer`, `detectors` (async workers), `opa`, `postgres` (+TimescaleDB), `redis`, `qdrant`, `bridge` (MCP/A2A/REST), `mcp-proxy`, `llm-proxy`, `dashboard`, `agents` (native network), `sandbox-runner`, `otel-collector`, `prometheus`, `grafana`, `jaeger`, `step-ca`. Profiles: `core` (minimum), `full`. Kubernetes (Helm chart in `deploy/`) is a P2 target with the same services.

`make run` starts the `core` profile with seeded contracts and demo agents; `make run-full` starts everything.

**Security of SentinelMesh itself:** keys in a secrets volume (dev) or Vault/KMS (production note), DB app role without UPDATE/DELETE on `events`, rate-limited public ports, admin endpoints behind operator role, no real secrets in the repo.

---

## 20. Attacks, demos and evaluation

### 20.1 Attack catalog (acceptance suite in `/attacks`, each has a test)

| ID | Attack | Expected outcome |
|---|---|---|
| A1 | Prompt injection in a retrieved document makes an agent attempt `shell.exec` | Deny (contract/untrusted-trigger), high alert, trust drop |
| A2 | Forged event signed with a wrong key | Rejected, critical `forged_event` |
| A3 | Delegation privilege escalation (agent asked to read `.env`) | Deny (delegation intersection), high |
| A4 | Secret exfiltration: Agent A reads secret, Agent B POSTs it externally | Deny (taint), critical, halt, lineage shown |
| A5 | Ping-pong loop between two agents | Collusion alert, throttle, quarantine on repeat |
| A6 | Goal drift (plan says summarize docs, agent starts outbound calls) | Drift + plan deviation alert, deny by contract |
| A7 | Burst of 50 calls in 5 s | Anomaly alert, throttle |
| A8 | Hand-edit a ledger row; separately, rewrite the whole DB consistently | Verify fails (chain/signature); full rewrite caught by external anchor mismatch |
| A9 | IDE agent adds a nonexistent package | Blocked/flagged (fake package), red diagnostic |
| A10 | Agent calls a non-existent API/symbol | Flagged by symbol resolution |
| A11 | Agent claims "all tests pass" when they fail | Claim contradicted after real test run, high finding |
| A12 | Agent writes hardcoded secret / SQL injection | Semgrep/Bandit finding, flagged or blocked at commit |
| A13 | IDE agent edits `.env` | Blocked by MCP proxy/PEP; if bypassed, detected by watcher and reverted |
| A14 | Two agents relay a secret through paraphrased messages | Taint n-gram/semantic detection plus collusion motif |
| A15 | Rogue agent mid-Bridge task | Halt, step reassigned, task completes, trace preserved |
| A16 | Risky shell command (`rm -rf`, `curl \| sh`) | Shadow simulation unsafe → deny |
| A17 | Memory poisoning: stored document plants an instruction | Untrusted provenance flagged, action requires approval/deny |
| A18 | Attestation drift: agent source modified mid-run | `attestation_drift` critical, halt |
| A19 | Replay accuracy | Re-evaluation matches recorded decisions 100% |

**Benign scenarios (B1–B20):** normal flows across all three demo networks and the Bridge. Expected: no deny/halt, measured for false positives.

### 20.2 Demo scenarios

1. **Multi-agent attack (PS002 core):** Planner → Retriever → Executor; injection blocked (A1), exfiltration halted (A4), collusion quarantined (A5), tamper check (A8), replay.
2. **IDE hallucination:** Cline/Cursor proposes a fake package (A9), fake API (A10), false test claim (A11), `.env` edit blocked (A13); sidebar shows claim-vs-reality.
3. **Collusion:** two agents loop or relay (A5, A14); graph detector flags; quarantine; replay.
4. **Agent Bridge (the showpiece):** in Cursor ask "Add Redis caching with tests and security review" → `delegate_task` → Planner, Coder, Tester, Reviewer, Security run under monitoring → hallucination checks → mid-flow violation (A15) halts a rogue agent and the step is reassigned → results stream back with agents used, trust scores, and audit trace → replay the cross-boundary trace.

### 20.3 Metrics (produced by `make benchmark` into `benchmark_results.json`)

| Metric | Target | Method |
|---|---|---|
| Detection latency | < 500 ms | event ts → alert ts |
| Enforcement latency | < 1 s | alert → halt/deny applied |
| Inline decision latency p95 | < 100 ms | PDP timings |
| False positive rate | < 10% | benign scenarios flagged/denied |
| Attack detection rate | > 90% | A1–A19 labelled outcomes |
| Hallucination detection rate | > 85% | seeded set: fake packages, fake APIs, false claims, insecure snippets |
| Shadow simulation catch rate | report | seeded risky commands |
| Overhead | < 15% | task time guarded vs unguarded |
| Audit completeness | 100% | signed events / total events |
| Replay accuracy | 100% | re-evaluation matches |
| Ledger verify after clean run | 100% | all four checks pass |

The benchmark is only credible if it runs the real pipeline over labelled data; the harness never mocks decisions.

---

## 21. Threat model and PS002 coverage

| Threat | Detection | Enforcement | Test |
|---|---|---|---|
| Prompt injection / tool misuse | Contract, provenance, injection score | Deny / approval | A1, A17 |
| Identity spoofing, forged events | Signatures, hash chain | Reject, alert | A2 |
| Agent code tampering | Attestation drift | Halt | A18 |
| Privilege escalation via delegation | Delegation intersection | Deny | A3 |
| Data exfiltration | Taint tracking | Deny, halt | A4, A14 |
| Collusion / loops | Graph motifs (+GNN) | Throttle, quarantine | A5 |
| Goal drift | Plan verifier, semantic drift | Flag, deny | A6 |
| Faulty / abusive behavior | Anomaly ensemble | Throttle | A7 |
| Log tampering / repudiation | Hash chain, Merkle, external anchor | Verify fails | A8 |
| Hallucinated dependencies/APIs/claims | Hallucination checks | Block, flag | A9–A12 |
| Dangerous commands | Shadow simulation | Deny | A16 |
| Unauthorized file changes | PEP, watcher, snapshots | Block / revert | A13 |
| Rogue agent in a delegated task | Controller + Bridge | Halt, reassign | A15 |

Every PS002 requirement in §1 maps to a row here and to at least one passing test; a requirement is marked covered only when its test passes in CI.

---

## 22. Workstreams (2 to 4 people) and interfaces

| Workstream | Owns |
|---|---|
| **W1 Integrity core** | `core/schemas`, event_bus, identity, ledger (Merkle, anchor), contracts, policy + `/policies` (OPA), pdp, enforcement, trust, snapshots, API/WebSocket |
| **W2 Detectors and evaluation** | verifier, anomaly, drift, provenance, collusion, injection, `ml/`, `attacks/`, `benchmark/`, replay re-evaluation |
| **W3 Instrumentation, Bridge, hallucination** | SDKs, MCP/LLM proxies, shell wrapper, watcher, git hooks, hallucination checks, shadow simulator, `bridge/` + native agent network |
| **W4 Frontend and IDE** | Dashboard (8 views), VS Code extension, JetBrains plugin, generated clients, docs, demo video, Grafana |

**Two people:** Person A = W1 + W2; Person B = W3 + W4. **Three:** merge W4 into whichever of W1–W3 is lightest.

**Contracts between workstreams (change only via this file + PR to both owners):**
1. `core/schemas` (event, decision, finding, alert) and the event hashing/signing rules in §5.2.
2. `openapi.yaml` and the WebSocket message kinds in §17.
3. Contract YAML schema and the OPA input/output shape in §8.
4. The `EventBus`, `PolicyEngine`, `AnomalyModel`, `VectorStore`, `IdentityProvider` interfaces.

**Dependency order of work:** (1) schemas, identity, ledger, bus → (2) API, SDK, PDP + OPA, enforcement, a fake agent, Live Ops view → (3) demo network, attacks A1–A3/A8, trust, taint → (4) remaining detectors, replay, Alerts/Agents/Ledger/Replay views → (5) MCP/LLM proxies, shell wrapper, watcher, hooks, hallucination checks, shadow simulator, snapshots/revert → (6) Bridge and native network, IDE Guard (VS Code), Bridge/IDE/Policies views → (7) P2 backends (GNN, autoencoder, SPIRE, NATS/Kafka, Cedar, JetBrains, K8s), benchmark, docs, demo recording.

---

## 23. Rules for coding agents

1. Follow this file, `core/schemas`, and `openapi.yaml` exactly. To change an interface, edit this file in the same commit and tell the other owners.
2. **No fake functionality.** No hardcoded alerts, decisions, findings, or metrics outside `scripts/seed_events.py`. Behavior must change when a contract, policy, or detector input changes.
3. Code against interfaces; vendor choices live in adapters.
4. Default deny. Fail closed for high-risk tools.
5. Work inside your workstream's directories. Small tasks, small commits, commit after every working step.
6. Every component ships with unit tests; every attack and benign scenario has an automated test; Rego policies have `opa test` coverage.
7. Never commit real secrets. Demo secrets must be obviously fake.
8. Label every control preventive or detective in code docs and UI.
9. When you finish or stop, update `PROGRESS.md`: done, in progress, next, known bugs.

---

## 24. Definition of done

- [ ] `make run` (core) and `make run-full` start cleanly; seeded demo works end to end
- [ ] Every row in §21 has a passing automated test and appears live in a demo
- [ ] A1–A19 produce expected outcomes through the real pipeline; B1–B20 produce no false denials beyond the target rate
- [ ] Ledger verify passes on a clean run and fails on tamper and full-rewrite attacks
- [ ] Halt, resume, quarantine release, approvals, revert, and snapshots work from dashboard and IDE
- [ ] MCP proxy and LLM proxy work with at least one real IDE agent (Cline or Cursor)
- [ ] Bridge `delegate_task` runs the six-agent pipeline with a mid-flow halt and reassignment
- [ ] VS Code extension shows diagnostics, sidebar, approvals; JetBrains plugin (P2) shows diagnostics and tool window
- [ ] Replay view re-evaluates decisions with 100% accuracy
- [ ] `make benchmark` writes `benchmark_results.json` and the README shows the table
- [ ] README has architecture diagram, preventive/detective table, threat model, results, demo video link
