# AegisMesh UI Improvement Plan

## 1. Objective

Redesign the current AegisMesh prototype into a credible enterprise security operations product. The result should feel like a mature tool used daily by security engineers—not a visually impressive concept dashboard.

The redesign will cover all five architecture-required views:

1. Live Operations
2. Agent Detail / Registry
3. Incident Detail
4. Forensic Replay
5. Audit Ledger / Blockchain Verification

The implementation should preserve the current React + Vite + Tailwind CSS v4 stack and existing functional navigation while substantially improving hierarchy, density, realism, and workflow clarity.

## 2. Chosen Product Direction

Use a restrained **enterprise security console** direction inspired by the product maturity of Wiz, CrowdStrike, Datadog, and modern cloud administration tools. These products are references for hierarchy and information design only; do not imitate their branding.

The interface should be:

- Data-first rather than decoration-first
- Dense enough for expert users but still readable
- Calm during normal operation and visually urgent only when intervention is required
- Consistent across tables, filters, detail panels, and investigation workflows
- Credible with realistic labels, states, timestamps, identifiers, and controls
- Designed around operator decisions rather than dashboard spectacle

## 3. Problems to Correct

The current implementation has several common generated-dashboard traits that should be removed:

- Too many cards with equal visual weight
- Generic dark navy and neon cyan “cybersecurity” styling
- Excessive uppercase labels, glows, badges, and rounded containers
- Decorative topology receiving more attention than actionable events
- Repeated card patterns where tables, lists, or split panes would be more useful
- Large fabricated metrics without sufficient trend, scope, or operational context
- Secondary screens behaving like presentation slides instead of working tools
- Severity color appearing too frequently, reducing its meaning
- Buttons and actions lacking clear primary/secondary/destructive hierarchy
- Inconsistent information density between views

## 4. Success Criteria

The redesign is successful when:

- A security operator can identify system health and the highest-priority problem within five seconds.
- A critical incident can be opened, understood, replayed, and traced to ledger evidence without losing context.
- Normal system states use neutral colors; red, amber, and green are reserved for semantic status.
- Every visible metric includes a timeframe, denominator, baseline, or comparison where applicable.
- The five views share one coherent navigation, typography, spacing, filter, table, and status system.
- Controls look intentional and have clear hover, focus, selected, disabled, and destructive states.
- The UI remains usable at laptop widths and degrades cleanly for narrow screens.
- There are no ornamental glows, gratuitous gradients, fake terminal motifs, or decorative charts without decision value.
- The final app passes the production build.

## 5. Visual Foundation

### 5.1 Color

Replace the current neon-led palette with neutral enterprise surfaces.

Use semantic design tokens rather than scattered color values:

- App background: near-black neutral charcoal
- Sidebar: slightly darker than the content canvas
- Primary surface: subtle elevation above the canvas
- Secondary surface: used for table headers, filters, and selected rows
- Border: low-contrast neutral border with a stronger hover/focus variant
- Primary text: high-contrast off-white
- Secondary text: cool neutral gray
- Muted text: lower-contrast gray that still passes accessibility requirements
- Brand accent: restrained teal used for selected navigation, focus, links, and primary actions
- Critical: red only for destructive states, blocked actions, and critical incidents
- Warning: amber for approvals, degraded states, and medium/high risk requiring attention
- Success: green for verified, allowed, and healthy states
- Informational: blue for neutral in-progress states

Remove colored glows and broad colored backgrounds. Status backgrounds should be subtle tints with readable foregrounds.

### 5.2 Typography

- Use one professional sans-serif family for interface text and one monospace family for hashes, IDs, timestamps, policy keys, and code.
- Reduce reliance on uppercase text. Reserve uppercase for very small metadata labels and compact status tags.
- Establish a predictable scale:
  - Page title
  - Section title
  - Body text
  - Supporting text
  - Metadata
- Use weight and spacing before color to establish hierarchy.
- Keep technical identifiers compact and copyable.

### 5.3 Spacing and Shape

- Use a consistent 4-point spacing rhythm.
- Reduce card padding and oversized empty areas.
- Use modest corner radii; tables and operational panels should not look like floating consumer cards.
- Prefer a small number of strong containers over many nested cards.
- Use dividers and column alignment to structure dense information.
- Use shadows sparingly or not at all; surface contrast and borders should do most of the work.

### 5.4 Icons

- Use one consistent outline icon style.
- Icons should clarify actions and status, not decorate headings.
- Do not use emoji.
- Ensure icon-only buttons have accessible labels and tooltips.

## 6. Shared Product Shell

### 6.1 Sidebar

Keep the persistent left navigation but simplify it:

- AegisMesh wordmark and small product mark at the top
- Primary navigation: Operations, Agents, Incidents, Replay, Audit Ledger
- Only Incidents may show an attention count
- Active state uses a restrained surface and left indicator, not a glow
- Move infrastructure health out of the sidebar card and into a compact footer status row
- Keep the signed-in user in a minimal footer area
- Support a compact collapsed state at narrower widths

### 6.2 Top Bar

- Add a useful global search affordance for agents, events, incidents, and hashes
- Show environment selector and connection state
- Keep notification access visually secondary
- Use breadcrumbs only on detail views, not as decoration on every page
- Avoid duplicating the current page name in both breadcrumbs and page title

### 6.3 Page Header

Every page should have:

- A clear title and one-line purpose
- Optional breadcrumb on detail views
- A compact timeframe or scope control where relevant
- No more than one primary action
- Secondary actions grouped in an overflow menu when they are not frequently used

### 6.4 Shared Filters

Create one reusable filter-bar pattern:

- Search
- Time range
- Severity
- Agent
- Decision/status
- “More filters” for uncommon fields
- Active filter chips with a clear-all action
- Filters should update visible mock data locally where practical

### 6.5 Status and Severity

Define a consistent vocabulary:

- Agent status: Active, Degraded, Halted, Quarantined, Offline
- Decision: Allow, Require approval, Sandbox, Block
- Incident severity: Critical, High, Medium, Low
- Verification: Verified, Pending, Failed
- Trust tier: Trusted, Watched, Restricted, Quarantined

Use compact semantic tags. Do not encode status by color alone; always include text or an icon.

### 6.6 Tables

All operational tables should share:

- Compact and comfortable density behavior, using compact by default
- Sticky column header where useful
- Consistent row hover and selected states
- Right-aligned numeric values
- Monospace timestamps, hashes, IDs, and sequence numbers
- Sort indicators
- Pagination or an explicit visible-record count
- Empty, loading, error, and no-results states in the component design
- Keyboard-visible focus states

## 7. View-by-View Redesign

### 7.1 Live Operations

Purpose: provide immediate system health and route operators to problems.

#### Layout

Use a three-part hierarchy:

1. Compact health summary
2. Active incidents and approvals
3. Live activity and agent state

#### Health Summary

Replace the five oversized metric cards with a single compact metric strip containing:

- Active agents: `2 of 3`
- Events/sec: current value plus 15-minute comparison
- Block rate: blocked actions divided by total actions
- Decision latency p95: current value and SLO
- Ledger status: verified through a stated sequence/checkpoint

Every metric must state its scope or timeframe. Use mini trends only when they help interpretation.

#### Priority Queue

Make the active critical incident the most visually prominent item, but keep it compact and actionable. Show:

- Severity
- Incident title
- Affected agent
- Attempted tool/action
- Detection time
- Containment status
- Primary action: Investigate

Add a smaller pending-approval row if the product data includes one. This demonstrates graduated enforcement without overwhelming the page.

#### Agent Mesh

Reduce the topology to a secondary operational module rather than the page centerpiece.

- Show Planner, Researcher, and Executor with clear status and trust tier
- Show delegation direction and the current active step
- Avoid animated or glowing connector lines
- Add a list/table alternative or accompanying details so the graph is not the only way to understand agent state
- Selecting an agent should open the agent view or a side panel

#### Live Event Stream

Promote the event stream to the main working area.

Columns:

- Time
- Agent
- Event
- Tool/resource
- Decision
- Risk
- Latency

Features:

- Pause/resume stream
- Filter controls
- Row selection
- Clear decision tags
- Details shown in a right-side inspector or expandable row

### 7.2 Agent Registry and Detail

Purpose: inspect identity, permissions, mission contract, trust, and recent behavior.

#### Registry

Replace three large profile cards with a compact table.

Columns:

- Agent and role
- Status
- Trust score and tier
- Active mission/session
- Current plan step
- Last event
- Contract version
- Actions menu

Selecting an agent opens a detail page or split-panel detail.

#### Agent Detail

Use these sections:

- Identity summary: ID, role, Ed25519 status, token expiry, attestation
- Status and operator actions: Halt, Resume, Quarantine, Release
- Trust: overall score plus compliance, integrity, consistency, claim accuracy
- Mission and current plan step
- Allowed capabilities and denied/high-risk tools
- Contract version and hash
- Recent actions
- Violations and trust history

Destructive actions must require confirmation. Quarantine should explain task reassignment and token revocation before confirmation.

### 7.3 Incident Detail

Purpose: answer what happened, why the system decided, what was contained, and what evidence proves it.

Use a stable investigation layout:

- Main evidence timeline on the left
- Persistent incident summary/response panel on the right

#### Incident Header

Show:

- Incident ID and severity
- Status: Contained, Investigating, Resolved
- Title
- Affected agent and session
- Detection time and containment duration
- Assigned owner if represented in the mock data

Actions:

- Primary: Open replay
- Secondary: Export evidence
- Overflow: mark resolved, copy incident link

#### Decision Summary

Show the attempted action and final decision clearly:

- Requested tool and arguments
- Decision: Deny + Quarantine
- Reason code
- Policy version
- Mission-alignment score
- Risk score
- Enforcement latency

#### Evidence Timeline

Create a chronological timeline from plan assignment through quarantine. Each step should expose relevant evidence rather than repeat generic statuses.

#### Policy Evaluation

Group facts into:

- Identity/token
- Mission contract
- Current plan
- Provenance/taint
- Behavior/anomaly
- OPA result and obligations

Clearly distinguish passed checks from violations. Avoid marking every non-pass row as visually critical.

#### Taint Lineage

Use a restrained data-flow representation:

`Untrusted web page → Researcher-01 → database.export → Blocked`

Allow each node to reveal source or event metadata. Ensure the blocked sink is visibly distinct.

#### Response Panel

Show:

- Containment state
- Trust change with reasons
- Token revocation
- Agent quarantine
- Task reassignment
- Workflow continuity

Release from quarantine must be a secondary/destructive-risk action with confirmation and prerequisites.

### 7.4 Forensic Replay

Purpose: reconstruct the incident deterministically and inspect state changes at each event.

Avoid a cinematic presentation. Make replay an analytical tool.

#### Layout

- Top: session metadata and verification status
- Center-left: event timeline
- Center: state/agent graph
- Right: selected event inspector
- Bottom: playback and scrubber controls

#### Timeline

Rows should show:

- Sequence and time
- Event type
- Agent
- Decision or state change
- Important trust/taint change

The selected event should control every other panel.

#### State Inspector

For the selected event, show:

- Before and after agent status
- Before and after trust score
- Current plan step
- Active taint labels
- Policy version used
- Recorded decision
- Deterministic re-evaluation result

If recorded and re-evaluated decisions differ, display a prominent integrity warning.

#### Playback

Keep play/pause, previous/next, speed, and a scrubber. Playback must visibly advance selected state. Controls must be keyboard accessible.

### 7.5 Audit Ledger

Purpose: prove event integrity and support independent verification.

#### Summary

Use a compact verification summary instead of four equal promotional cards:

- Overall ledger status
- Last verified sequence
- Hash-chain continuity
- Signature verification
- Current Merkle checkpoint
- Blockchain anchor state

#### Event Table

Columns:

- Sequence
- Timestamp
- Event type
- Agent
- Event hash
- Checkpoint
- Signature/proof status

Selecting a row opens an evidence inspector showing:

- Full event hash
- Previous hash
- Content hash
- Agent signature
- Core signature
- Merkle inclusion path
- Root/checkpoint
- Blockchain transaction and chain ID

Provide explicit copy controls for long identifiers.

#### Verify Ledger Workflow

“Verify ledger” should trigger a visible local verification sequence:

1. Checking event hashes
2. Checking chain continuity
3. Verifying signatures
4. Verifying Merkle roots
5. Comparing blockchain anchor

Represent progress, success, and failure states. On success, report number of checked events and completion time. On failure, identify the first invalid sequence and provide a route to inspect it.

## 8. Interaction Requirements

Implement meaningful client-side interactions using the existing mock data:

- Sidebar view navigation
- Search/filter behavior for at least the event, agent, incident, and ledger tables
- Selectable table rows
- Agent or event details in a side panel, drawer, or expanded row
- Pause/resume event stream state
- Incident-to-replay navigation
- Replay play/pause, previous/next, speed, and event selection
- Ledger verification progress and completed state
- Copy actions for IDs and hashes, with concise success feedback
- Confirmation dialog for destructive actions such as quarantine release or halt

Do not add interactions that appear functional but do nothing. If an action is outside the prototype scope, render it disabled with an explanation or omit it.

## 9. Component and Code Structure

The current application is concentrated in `src/App.tsx`. Refactor enough to make the redesign maintainable without introducing unnecessary architecture.

Recommended structure:

- `src/App.tsx` — app shell and current-view routing/state
- `src/components/AppShell.tsx`
- `src/components/PageHeader.tsx`
- `src/components/FilterBar.tsx`
- `src/components/StatusTag.tsx`
- `src/components/DataTable.tsx`
- `src/components/MetricStrip.tsx`
- `src/components/DetailPanel.tsx`
- `src/components/ConfirmDialog.tsx`
- `src/components/Icon.tsx`
- `src/views/OperationsView.tsx`
- `src/views/AgentsView.tsx`
- `src/views/IncidentView.tsx`
- `src/views/ReplayView.tsx`
- `src/views/LedgerView.tsx`
- `src/data/mockData.ts`
- `src/types.ts`
- `src/index.css` — Tailwind import, font imports, global tokens, and truly global styles

If the existing application remains small enough, closely related primitives may be grouped, but avoid returning to one monolithic file.

Use explicit TypeScript types for:

- Agent
- Event
- Incident
- Decision
- Trust dimensions
- Ledger event
- Replay event
- Severity and status enums/unions

Keep mock data separate from presentation components so a future API layer can replace it cleanly.

## 10. Responsive Behavior

Primary target: professional desktop and laptop use.

- At wide widths, use persistent navigation and multi-column investigation layouts.
- At medium laptop widths, preserve tables and use horizontal overflow only when necessary.
- Collapse the sidebar to icons before reducing data readability.
- Move right-side inspectors below content or into a drawer at narrow widths.
- Allow nonessential table columns to hide based on priority.
- Do not convert every table into disconnected cards on mobile; preserve row relationships.
- Ensure primary actions remain reachable without sticky overlays covering data.

## 11. Accessibility

- Meet WCAG AA contrast for text and controls.
- Use semantic controls and accessible names.
- Add visible keyboard focus states.
- Do not communicate status through color alone.
- Support keyboard navigation for tabs, table row actions, replay controls, dialogs, and drawers.
- Use `aria-live` for ledger verification completion and copy feedback where appropriate.
- Respect reduced-motion preferences; avoid unnecessary motion entirely.

## 12. Content and Data Realism

Retain the architecture’s primary demo narrative:

- Mission: research Redis caching strategies and produce a verified report
- Planner delegates research and report tasks
- Researcher consumes untrusted content
- Researcher attempts `database.export("customers")`
- The action is denied
- Trust falls from 94 to 34
- The Researcher is quarantined
- Remaining workflow continues
- Evidence is signed, checkpointed, and verifiable

Use coherent timestamps, event sequences, policy versions, hashes, agent IDs, and session IDs across every view. The same incident must not have conflicting details on different screens.

Avoid random vanity metrics. Every mock value should support the narrative or demonstrate a documented architecture capability.

## 13. Implementation Sequence

1. Define shared semantic tokens, typography, spacing, and responsive breakpoints.
2. Extract TypeScript models and coherent mock data.
3. Build shared primitives: buttons, status tags, filters, tables, icons, dialogs, and detail panels.
4. Rebuild the application shell and navigation.
5. Rebuild Live Operations, beginning with the event stream and priority queue.
6. Rebuild Agent Registry and Agent Detail.
7. Rebuild Incident Detail and ensure all evidence matches the shared event data.
8. Rebuild Forensic Replay around selected-event state.
9. Rebuild Audit Ledger and verification workflow.
10. Add responsive behavior, keyboard states, and empty/loading/error component states.
11. Perform a final consistency pass across language, status colors, spacing, and identifiers.
12. Run the production build and repair all failures.

## 14. Verification Strategy

### Functional Checks

- Every sidebar destination loads the intended view.
- Filters change visible records and clear correctly.
- Event and ledger rows can be selected and inspected.
- Incident actions navigate to the matching replay/session.
- Replay advances through all events and updates selected state.
- Ledger verification shows progress and a deterministic final result.
- Confirmation dialogs prevent accidental destructive actions.
- Copy controls copy the complete underlying identifier, not the truncated display value.

### Visual Checks

Review at representative desktop, laptop, and narrow widths:

- No clipped controls or unreadable columns
- Clear page and section hierarchy
- Severity colors used only where semantic
- No excessive glows, gradients, or nested cards
- Consistent status tags and action hierarchy
- Tables align correctly and remain scannable
- Long hashes and identifiers truncate without breaking layout

### Technical Checks

- Run the repository’s production build command: `pnpm run build`
- Resolve all TypeScript and Vite build failures
- Confirm there are no console errors during the core navigation and interaction flows
- Do not start a second development server; use the environment’s existing Vite server and hot reload

## 15. Out of Scope

This redesign does not require:

- A real backend, WebSocket, Redis, PostgreSQL, OPA, or blockchain connection
- Authentication or authorization implementation
- Real cryptographic verification
- Persisting state across reloads
- Additional views beyond the five architecture-defined product areas
- Marketing pages, onboarding, pricing, or documentation surfaces
- A new component library dependency unless an existing project dependency already provides the required capability

The frontend should, however, maintain clean data boundaries so real API and WebSocket data can replace mock data later without redesigning the UI.
