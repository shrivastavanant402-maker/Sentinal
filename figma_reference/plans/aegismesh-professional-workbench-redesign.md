# AegisMesh Professional Workbench Redesign Plan

## Objective

Rebuild AegisMesh into a polished enterprise security operations product with the quiet precision and structural quality associated with Linear and Vercel. This is a full structural redesign, not another palette adjustment.

The primary issue to solve is the generated-dashboard feeling created by repeated bordered cards, equal-weight modules, tiny typography, and excessive local section framing. The replacement will use one integrated workbench per view: continuous surfaces, docked inspectors, functional dividers, compact toolbars, and a clear primary workflow.

All existing product behavior remains available. Labels, supporting metadata, and information grouping may be refined to improve credibility and usability.

## Confirmed Direction

- Use an integrated workbench rather than a collection of floating cards.
- Keep a refined, labeled left sidebar.
- Use Linear/Vercel as the quality reference: quiet, precise, highly structured, and minimally decorative.
- Allow substantial structural changes across all five views.
- Preserve existing stateful behavior and underlying mock records.
- Allow copy and metadata improvements where they make the interface more credible.
- Preserve automatic light/dark adaptation with `prefers-color-scheme`.
- Use warm-neutral light mode and a restrained neutral dark counterpart.
- Retain muted indigo for interaction and selection; semantic colors remain reserved for actual state.
- Maintain balanced professional density rather than extremely compact SIEM density.
- Do not add a component library, chart package, routing package, or backend.

## Repository Findings and Root Causes

### Current architecture

- `src/App.tsx` contains shared primitives, the shell, all five views, and their interaction state.
- `src/index.css` contains adaptive light/dark tokens, all component styling, and responsive rules.
- `src/data.ts` and `src/types.ts` contain coherent mock records and models.
- Current behavior includes view switching, filtering, row selection, copy actions, replay playback, ledger verification, and a destructive confirmation dialog.

### Why the current interface still feels generated

- `panel` and `section-heading` are applied repeatedly, causing almost every region to become an equally weighted bordered card.
- Metrics, alerts, tables, inspectors, evidence, and supporting context all use nearly identical containers despite having different semantic importance.
- Many visible labels and supporting values render at 8–10px, making the app feel miniaturized rather than professionally dense.
- Borders and rounded rectangles establish most of the hierarchy instead of typography, alignment, whitespace, and workflow order.
- Each view reads as a stack of dashboard modules instead of a purpose-built operational tool.
- The right-side content is often another card column rather than a stable contextual inspector.
- Toolbars, tables, detail regions, and summaries do not share one continuous workspace frame.
- The theme system is now adaptive, but color quality alone cannot solve the structural problem.

## Design Foundation

### Typography

Keep Inter and JetBrains Mono, but rebuild the scale:

- Product/page title: approximately 20–22px with compact line height and medium/semibold weight.
- Section title: 13–14px, not uppercase.
- Primary body/table text: 12–13px.
- Secondary metadata: 11–12px.
- Small labels: no smaller than 10–11px except purely auxiliary counters.
- Monospace remains limited to timestamps, IDs, hashes, policy names, and executable actions.
- Reduce uppercase usage to occasional column labels or tiny category labels.

The result should feel dense because of alignment and layout efficiency, not because the type is unusually small.

### Spacing and geometry

- Use a 4px base spacing rhythm with common gaps of 8, 12, 16, 20, and 24px.
- Use modest 4–6px radii for controls and only slightly larger radii for overlays.
- Remove rounded corners from internal table rows, panes, and stacked sections.
- Use borders primarily as structural dividers, not as outlines around every content group.
- Keep shadows limited to dialogs, menus, and genuinely elevated overlays.

### Color and themes

- Retain the existing semantic token strategy, but simplify surface levels to canvas, workspace, inset, hover, selection, and overlay.
- Light mode uses a warm off-white shell and crisp workspace surface.
- Dark mode uses near-black neutral framing and controlled charcoal workspaces.
- Indigo is used only for focus, selected navigation, primary action, selected row, and active replay position.
- Red, amber, green, and blue are used only for state, not decoration.
- Every state remains identifiable through text, icon/dot, and placement rather than color alone.

## Shared Component and Layout Strategy

Refactor the visual primitives in `src/App.tsx` and `src/index.css` around a small workbench system.

### Application shell

- Keep a fixed labeled sidebar at roughly 208–220px on wide screens.
- Simplify the brand area into a quiet product mark and name; remove decorative framing that competes with navigation.
- Group navigation under a subtle workspace label and keep the incident count as the only attention badge.
- Make active navigation clear with weight, icon color, a subtle selection fill, and a narrow indigo edge.
- Place environment and user information in a calm sidebar footer without making it another card.
- Replace the current generic top bar with a workspace toolbar integrated into the main area:
  - current section/context at left;
  - global command/search field in the center or flexible region;
  - production state and notifications at right.

### Workspace frame

Introduce shared structural patterns, implemented as local React components or consistent markup/classes:

- `WorkspaceHeader`: breadcrumb/context, title, concise description, and actions.
- `WorkspaceSurface`: one primary bordered surface per view, not one per subsection.
- `WorkspaceToolbar`: filters, scope/time range, search, counts, and utility controls.
- `SummaryRail`: inline metrics separated by dividers rather than metric cards.
- `SplitWorkspace`: master region plus docked contextual inspector.
- `InspectorHeader` and `InspectorSection`: structured detail groups inside a stable side pane.
- `DataTable`: consistent table header, row, selected state, empty state, and footer.
- `Status`: keep semantic text plus dot, but improve sizing and alignment.
- `NoticeRow`: inline critical/approval/verification states without card styling.

Avoid introducing abstractions that only wrap one element. Shared patterns should remove repeated layout decisions across views.

### Controls

- Increase control height to approximately 32–34px and improve internal spacing.
- Make primary actions rare and clearly prioritized.
- Secondary actions use neutral borders; ghost actions remain visually quiet until hover.
- Search and filters share one toolbar language.
- Use visible, accessible focus rings in both themes.
- Keep copy actions compact and contextual.

## View-by-View Structural Redesign

### 1. Live Operations

This becomes the product’s flagship operational workbench.

#### Header and summary

- Use a compact workspace header with “Live operations,” a one-line mission/system description, and the time range at the right.
- Replace the five bordered metric cells with a single inline summary rail beneath the header.
- Keep the same values, but establish importance through typography:
  - active agents;
  - throughput;
  - block rate;
  - p95 decision latency;
  - ledger verification.
- Supporting comparisons remain visible but no longer compete with the primary values.

#### Attention queue

- Place “Needs attention” as a concise queue directly above runtime activity.
- Render the critical incident and approval request as two full-width operational rows separated by dividers, not nested cards.
- Give the critical incident stronger text hierarchy and a restrained semantic edge/marker rather than a large red background.
- Preserve Investigate and Review actions.

#### Runtime workspace

- Use one continuous workbench containing:
  - toolbar with local search, agent, decision, time range, stream state, and record count;
  - runtime event table as the dominant region;
  - docked event inspector at the right when a row is selected.
- Integrate Pause/Resume into the table toolbar rather than the section heading.
- Keep the inspector aligned to the table header and rows so it reads as contextual detail, not a separate dashboard card.
- Move agent posture and active mission into compact inspector tabs or stacked inspector sections below event details, avoiding an extra card column.
- Preserve filtering, row selection, copy, and ledger navigation behavior.

### 2. Agents

Turn the page into a true registry/detail master-detail workspace.

- Use one workspace surface below the header.
- Place search, status scope, and Register Agent in the toolbar.
- Keep the agent registry in a fixed or proportional left/master region.
- Dock selected-agent detail to the right instead of placing it beneath the table.
- Registry rows show identity, status, trust, current step, and last activity; less important contract data can move into the detail pane at narrower widths.
- Detail pane structure:
  - compact identity header with status and actions;
  - mission and current step;
  - verified identity and contract metadata;
  - capabilities as a low-emphasis list/chip group;
  - overall trust and four dimensions using understated tracks.
- Preserve Halt Agent and conditional Release Quarantine actions.
- Preserve the existing confirmation dialog and improve its hierarchy and focus treatment.
- On narrow screens, the selected detail stacks immediately after the registry with a clear selected-agent heading.

### 3. Incident Detail

Reframe the page as a focused case file rather than a collection of evidence cards.

- Use the incident ID as breadcrumb/context and the incident title as the primary heading.
- Keep Export Evidence secondary and Open Replay primary.
- Add a compact case metadata strip for severity, containment, detection time, and response duration.
- Use a two-column workbench:
  - main evidence timeline and policy evaluation;
  - docked case inspector for response state, trust impact, and provenance.
- Replace the six equal decision tiles with one decision block:
  - attempted action and enforcement decision receive primary emphasis;
  - reason code, policy version, mission alignment, and risk become aligned supporting fields.
- Render the evidence timeline as a continuous chronological list with one vertical guide and restrained critical markers.
- Render policy evaluation as a compact audit table/list inside the same main workbench, separated by a divider rather than another card.
- Case inspector sections use headers and spacing rather than boxed subcards.
- Preserve navigation to Forensic Replay.

### 4. Forensic Replay

Make replay feel like a specialized analysis tool.

- Use a full-width, near-viewport-height workbench below a compact header.
- Keep three regions at wide widths:
  - event sequence rail on the left;
  - execution/state canvas in the center;
  - state inspector on the right.
- Use structural dividers between panes rather than gaps and rounded cards.
- Event rail uses compact chronological rows with selected and critical markers.
- Central canvas uses a subdued execution path with agent identity, current state, and selected event context; remove presentation-style card framing around each agent.
- Integrate event count, scrubber, previous/play/next, and speed into one persistent bottom playback bar.
- State inspector uses aligned before/after values, policy version, and re-evaluation result.
- Preserve event selection, previous/next, autoplay, pause, scrubber navigation, and speed behavior.
- On narrower screens, panes stack in workflow order while playback remains attached to the replay surface.

### 5. Audit Ledger

Turn the ledger into a dense verification and evidence workbench.

- Use a compact header with Verify Ledger as the only primary action.
- Replace four summary cards with a single metadata rail for chain status, checkpoint, event count, and anchor.
- Verification progress appears as a slim inline state row above the toolbar and collapses into a completed confirmation when done.
- Main workspace contains:
  - toolbar with search and additional filters;
  - ledger table as the master region;
  - docked cryptographic evidence inspector.
- Evidence values use aligned labels, full-value tooltips/title behavior where appropriate, truncation, and compact copy actions.
- Inclusion proof becomes the final inspector section, not a separate success card.
- Preserve deterministic five-stage verification, row selection, record counts, and full-value copying.

## Content Refinement

Improve visible copy without changing the underlying data model or product meaning:

- Use sentence case consistently.
- Shorten repetitive descriptions and section subtitles.
- Replace vague labels such as “Event” where “Action” or “Policy event” is clearer.
- Use consistent terminology for status, trust, containment, policy decisions, and verification.
- Keep identifiers, timestamps, hashes, policies, and resources realistic and internally consistent.
- Add only supporting metadata derivable from existing mock content; do not invent new backend behavior.

## State and Data Flow Preservation

Keep the existing React state model unless structural extraction makes a small prop boundary useful:

- `App` continues to own the active `View` and confirmation-dialog visibility.
- `OperationsView` retains query, agent, decision, paused, selected event, and filtered event derivation.
- `AgentsView` retains search and selected-agent state.
- `ReplayView` retains selected event index, playing state, speed, and timer cleanup.
- `LedgerView` retains query, selected event, verification step, timer progression, and completed state.
- Navigation callbacks continue to connect Operations → Incident, Incident → Replay, and event evidence → Ledger.
- Copy behavior continues to write the complete value, even when display text is truncated.

No routing, persistence, backend calls, or global state library will be added.

## File Scope

### `src/App.tsx`

- Restructure the application shell and all five view layouts.
- Refine local shared primitives and introduce only the workbench components used across multiple views.
- Preserve state, filtering, timers, handlers, and navigation behavior.
- Update labels and supporting metadata where approved.

### `src/index.css`

- Rebuild component styles around the integrated workbench model.
- Retain and refine adaptive light/dark semantic tokens.
- Raise the typography floor and normalize spacing/control sizing.
- Remove obsolete card-specific styles after markup migration.
- Rebuild responsive pane behavior and table overflow rules.

### `src/data.ts` and `src/types.ts`

- Keep the data model unchanged.
- Only adjust mock display strings if necessary for terminology consistency; no new data architecture is planned.

### No changes

- No new dependencies.
- No Vite, Tailwind, TypeScript, or build configuration changes.
- No backend, routing, authentication, or persistence work.

## Responsive Behavior

- Wide desktop: labeled sidebar and full multi-pane workbenches.
- Laptop: retain labeled sidebar where practical; reduce inspector widths and metric spacing.
- Tablet: collapse sidebar to icon navigation; stack or overlay contextual inspectors below the master surface.
- Narrow screens: preserve logical workflow order, allow operational tables to scroll horizontally, and make header actions wrap without clipping.
- Do not hide columns whose absence would make records ambiguous; move secondary fields into detail regions only where the selected record remains understandable.
- Keep controls reachable and text readable without shrinking below the new type floor.

## Accessibility and Interaction States

- Maintain semantic dialog roles and `aria-live` verification updates.
- Keep visible focus indicators in both themes.
- Preserve keyboard-reachable native buttons, inputs, and selects.
- Ensure selected rows, active navigation, severity, and verification states are not color-only.
- Maintain readable contrast for body, metadata, placeholders, and disabled controls.
- Respect `prefers-reduced-motion` and avoid ornamental animation.
- Keep target sizes reasonable despite the denser layout.

## Edge Cases and Failure Modes

- Empty event/filter results must retain a clear empty state inside the workbench.
- Closing the Operations inspector must allow the table to use the available width cleanly.
- Long resources, contracts, policy names, and hashes must truncate without breaking grid alignment.
- Copy controls must remain available for complete values.
- Replay timers must continue to stop at the end and clean up on state changes/unmount.
- Ledger verification must disable duplicate starts while active and remain deterministic.
- Theme changes must continue to follow device preference without React state or reload.
- Dialog content and actions must remain usable at narrow widths.

## Verification Strategy

1. Use the existing supervised Figma Make development server; do not start another development server.
2. Inspect all five views in light and dark device preferences.
3. Validate desktop, laptop, tablet, and narrow widths, focusing on pane sizing, overflow, table alignment, and action wrapping.
4. Exercise all preserved behavior:
   - five-view navigation;
   - Operations filtering, selection, pause/resume, incident navigation, and ledger navigation;
   - agent search, selection, and quarantine dialog;
   - Incident → Replay navigation;
   - replay selection, scrubber, previous/play/pause/next, and speed;
   - ledger search, row selection, copy, and verification completion.
5. Check hover, focus-visible, selected, disabled, destructive, empty, in-progress, and completed states.
6. Audit the final UI for repeated card framing, tiny labels, unnecessary uppercase, excessive semantic color, and inconsistent dividers.
7. Run `pnpm run build` and repair all introduced TypeScript, JSX, CSS, or Vite failures until it passes.
8. Run `git diff --check` to catch whitespace or patch issues.

## Completion Criteria

- Each view reads as a purpose-built operational workspace rather than a dashboard assembled from cards.
- Live Operations clearly establishes the product’s quality bar and primary workflow.
- Typography is readable and deliberate; density comes from structure, not 8px text.
- Tables, toolbars, inspectors, headers, and detail regions use one coherent system.
- Light and dark modes both feel intentionally designed.
- Important states are clear without excessive red, amber, green, or indigo.
- Existing interactions and data remain functional.
- Responsive layouts remain usable and the production build passes.
