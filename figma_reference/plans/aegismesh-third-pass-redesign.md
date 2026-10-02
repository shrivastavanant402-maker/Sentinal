# AegisMesh Third-Pass Product Redesign Plan

## Objective

Redesign all five AegisMesh product views into a credible, production-quality security operations console while preserving the current mock data, navigation destinations, and interaction behavior. The result should feel quiet, precise, and intentionally designed rather than like a themed dashboard: dark neutral surfaces, a restrained muted-indigo accent, balanced expert density, and a strong workspace hierarchy inspired by mature tools such as Linear without copying their branding.

## Confirmed Decisions

- Preserve behavior and existing workflows; redesign the presentation and information architecture around them.
- Keep the product dark-theme-only for this pass.
- Use muted indigo only for selection, focus, links, and primary actions.
- Reserve red, amber, and green for true semantic states.
- Use a compact sidebar plus a contextual top bar.
- Target balanced professional density rather than an ultra-compact SIEM or a spacious executive dashboard.
- Retain the five current views: Live Operations, Agents, Incident Detail, Forensic Replay, and Audit Ledger.
- Do not add a UI library or backend integration.

## Repository Findings

- The implementation is concentrated in `src/App.tsx`, with shared mock records in `src/data.ts`, models in `src/types.ts`, and the complete visual system in `src/index.css`.
- The repository has no external component/design-system dependency. Existing local primitives include `Button`, `Input`, `Select`, `Status`, `CopyButton`, `PageHeader`, `FilterBar`, and table patterns.
- Existing behavior to preserve includes view switching, global and local search state, event/agent/ledger row selection, operation filters, stream pause/resume, incident-to-replay navigation, replay stepping/autoplay/speed, ledger verification progress, copying hashes, and the quarantine confirmation dialog.
- The current build has a clean Git working tree. The running development server must not be started or replaced.

## Implementation Plan

### 1. Rebuild the visual foundation in `src/index.css`

- Replace the teal-led tokens with a neutral charcoal ramp and muted-indigo interaction tokens.
- Define a disciplined semantic token set for canvas, raised and inset surfaces, subtle/strong borders, primary/secondary/muted text, focus, danger, warning, success, and informational states.
- Normalize the sizing language around compact controls, restrained corner radii, low-contrast dividers, and minimal elevation; remove ornamental surface treatments and avoid gradients/glows.
- Keep Inter for interface text and JetBrains Mono for hashes, IDs, timestamps, and policy expressions, but improve type scale, line-height, weight, and letter spacing so tiny labels are readable and hierarchy does not depend on uppercase styling.
- Establish consistent states for hover, active, selected, disabled, focus-visible, and destructive controls.
- Keep motion limited to meaningful transitions such as verification progress and panel state; respect `prefers-reduced-motion`.

### 2. Refine shared primitives and the application shell in `src/App.tsx`

- Preserve the local primitive API where practical, but adjust markup/classes so controls and status treatments share one coherent system.
- Redesign the shell as:
  - a compact, fixed sidebar with clear product identity, five navigation destinations, a restrained incident count, and environment/user information;
  - a slim contextual top bar with the current section identity, global search, production status, and utility actions;
  - a wider, calmer content canvas with consistent maximum readable width and page gutters.
- Make the active destination obvious through structure and indigo selection rather than bright fills.
- Redesign page headers to separate breadcrumb/context, title, supporting copy, and actions without oversized hero-like spacing.
- Consolidate panel, section-heading, toolbar, table, badge, key-value, and inspector patterns so every view uses the same visual grammar.
- Continue using the existing inline icon system; do not introduce icon or component dependencies.

### 3. Redesign Live Operations as the primary operator workspace

- Keep the existing health metrics, but render them as a quiet operational summary rail rather than five equal dashboard cards.
- Make “Needs attention” the strongest content immediately below the header, with the critical incident visually dominant and the approval request secondary.
- Rework Runtime Activity into the principal surface: compact filter toolbar, clear table header, aligned numeric/monospace columns, precise row hover/selection, and an integrated stream pause state.
- Keep the selected-event inspector and supporting agent/mission information, but reduce nested-card styling and use a deliberate master-detail layout.
- Ensure the highest-priority incident and system health can be understood within the first screen without overusing critical color.

### 4. Redesign Agents as a registry with an integrated detail workspace

- Keep searchable agent selection and the existing selected-agent state.
- Present the registry as a compact table/list with identity, operational status, trust, current step, last event, and contract optimized for scanning.
- Turn agent details into a structured split workspace rather than a second standalone dashboard card:
  - identity, contract, mission, capability token, and capabilities in one information group;
  - overall trust and trust dimensions in a second group with subtle neutral tracks and semantic exceptions;
  - halt/release actions placed consistently in the detail header.
- Preserve the existing quarantine-release confirmation dialog and make its destructive hierarchy, overlay, keyboard focus visibility, and explanatory copy feel deliberate.

### 5. Redesign Incident Detail around investigation flow

- Establish incident identity, containment state, timestamps, and key actions in a compact case header.
- Convert the decision summary into a focused evidence summary with the attempted action, enforcement decision, reason, policy, mission alignment, and risk arranged by importance rather than as six equal tiles.
- Make the signed evidence timeline the main reading path, with restrained markers and a precise visual break around the causal/critical sequence.
- Keep policy evaluation and contextual metadata as supporting evidence surfaces with consistent status semantics.
- Preserve Export Evidence and Open Replay actions; keep Open Replay as the primary continuation of the investigation.

### 6. Redesign Forensic Replay as a purpose-built three-pane analysis tool

- Keep selected-event state, previous/play/next controls, playback speed, and autoplay behavior unchanged.
- Use a compact event rail on the left, a central replay/state canvas, and a structured state inspector on the right at wide widths.
- Replace the presentation-like agent flow with a quieter execution-path visualization that emphasizes the currently affected agent and decision without decorative effects.
- Integrate event position, scrubber, and playback controls into one coherent timeline control area.
- Make before/after trust and policy re-evaluation changes easy to compare, using critical color only when the value actually deteriorates.
- At narrower widths, stack panes in workflow order: event list, replay canvas/controls, then inspector.

### 7. Redesign Audit Ledger as a verification workspace

- Keep search, selectable ledger rows, proof inspection, copy controls, and the deterministic five-step verification workflow.
- Present verification status as a compact integrity banner with clear in-progress and completed states, not a celebratory dashboard element.
- Rework the summary into a subdued metadata strip covering chain continuity, checkpoint, and blockchain anchor.
- Make the ledger table the dominant surface and the selected evidence/proof inspector a stable companion pane.
- Improve long-hash truncation and alignment while ensuring copy actions retain the complete underlying value.

### 8. Responsive and accessibility pass

- Maintain the full labeled compact sidebar on desktop, collapse it to icon navigation at laptop/tablet widths, and avoid obscuring the workspace at narrow widths.
- Collapse multi-pane views into a logical vertical order while retaining context and actions.
- Allow data tables to scroll horizontally where hiding columns would remove operational meaning; keep essential identity/status columns readable.
- Ensure long hashes, resource names, policy IDs, and mission text truncate or wrap without breaking layout.
- Retain semantic labels, `aria-live` for verification, dialog semantics, visible focus states, and reduced-motion handling.
- Confirm readable contrast for muted text and avoid encoding status by color alone.

## File Scope

- `src/App.tsx`: restructure the shell and all five view layouts; refine shared local primitives while preserving state and event handlers.
- `src/index.css`: replace the visual token system and responsive/component styling for the new experience.
- `src/data.ts` and `src/types.ts`: leave unchanged unless a small presentational label correction is required; no new backend or data model is planned.
- No new dependencies, routes, documentation files, or build configuration changes.

## Behavior Preservation Checklist

- All five sidebar destinations switch to the correct view.
- Operations text, agent, and decision filters continue to filter records.
- Pause/resume updates the stream-control state.
- Event rows, agent rows, replay events, and ledger rows remain selectable.
- Incident investigation navigates to Incident Detail and Open Replay navigates to Forensic Replay.
- Replay previous/play/pause/next, scrubber selection, and speed selection continue to work.
- Ledger verification advances through all five checks and reaches the completed state.
- Hash copy controls copy full values.
- Quarantine release opens and closes the confirmation dialog without changing the current mock behavior.

## Verification Strategy

1. Use the existing supervised preview/hot reload; do not start another development server.
2. Check representative desktop, laptop, and narrow widths in the preview for hierarchy, overflow, table readability, pane stacking, and control reachability.
3. Exercise the behavior-preservation checklist across all five views.
4. Check hover, selected, focus-visible, disabled, destructive, verification-progress, and dialog states.
5. Run the repository-prescribed production check: `pnpm run build`.
6. Fix any TypeScript, JSX, CSS, or Vite failures introduced by the redesign and rerun the build until it succeeds.

## Completion Criteria

- The product reads as one coherent enterprise console rather than five separately styled screens.
- A user can identify current health and the critical incident within five seconds on Live Operations.
- Muted indigo is the sole interaction accent; semantic colors appear only for meaningful state.
- The default screen is balanced and information-dense without tiny, low-legibility typography.
- Tables, inspectors, toolbars, headers, and actions are consistent across views.
- Existing interactions work unchanged, layouts remain usable at laptop and narrow widths, and the production build passes.
