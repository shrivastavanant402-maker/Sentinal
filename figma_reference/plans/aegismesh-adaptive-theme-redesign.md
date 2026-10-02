# AegisMesh Adaptive Light and Dark Theme Redesign Plan

## Objective

Redesign AegisMesh around a polished warm-neutral light theme while also refining the dark theme into an equal-quality counterpart. The application will follow the operating system or browser preference automatically through `prefers-color-scheme`; there will be no manual theme toggle in this pass. Existing product behavior and information architecture remain intact.

The target is a credible enterprise operations product rather than a visually themed dashboard: crisp work surfaces, disciplined density, strong table hierarchy, excellent legibility, restrained muted-indigo interaction states, and semantic colors used only when operationally meaningful.

## Confirmed Product Decisions

- Support both light and dark themes.
- Select the active theme automatically from the user’s device preference.
- Do not add a manual theme selector or persist a preference.
- Use a warm-neutral enterprise direction for light mode.
- Refine both themes together rather than treating dark mode as an unchanged fallback.
- Preserve the compact sidebar, contextual top bar, five current views, mock data, and existing interactions.
- Keep muted indigo as the product interaction accent in both themes.
- Maintain balanced professional density.
- Do not add a component library, theme package, or JavaScript theme state.

## Current Repository Facts

- `src/App.tsx` contains the application shell, shared local primitives, all five product views, and interaction state.
- `src/index.css` contains the complete visual system and responsive behavior.
- `src/data.ts` and `src/types.ts` contain reusable mock records and models and do not need theme-related changes.
- The current CSS already centralizes most colors as custom properties, so automatic theming can be implemented without duplicating component rules.
- The app uses Inter for interface text and JetBrains Mono for hashes, timestamps, IDs, and policy expressions.
- The existing development server is supervised by Figma Make and must not be started manually.

## Implementation Plan

### 1. Convert the CSS foundation to light-first semantic tokens

Update `src/index.css` so the default `:root` values form the warm-neutral light theme:

- Page canvas: warm off-white rather than pure white.
- Sidebar and top bar: subtly differentiated neutral surfaces, not high-contrast decorative blocks.
- Primary work surfaces: crisp white with understated neutral borders.
- Raised, muted, hover, selected, and inset surfaces: a coherent warm-gray progression.
- Text: graphite primary text, neutral secondary text, and accessible muted text.
- Accent: restrained indigo for selected navigation, focus rings, primary actions, links, active scrubbers, and selected records.
- Semantic tones: calibrated red, amber, green, and blue with corresponding subtle backgrounds and borders.
- Shadows: use only for overlays or genuinely elevated elements; rely on borders and surface contrast for normal panels.

Add `color-scheme: light dark` at the document level so native controls and browser-rendered UI can adapt correctly.

### 2. Add an automatic dark token override

Add a single `@media (prefers-color-scheme: dark)` block that overrides semantic custom properties rather than duplicating component selectors.

The dark palette will be revised alongside light mode:

- Neutral near-black canvas with low-chroma charcoal surfaces.
- Sufficient surface separation without relying on bright outlines.
- Softer off-white text and improved secondary/muted text contrast.
- Indigo adjusted for dark-background accessibility without appearing neon.
- Semantic tones tuned independently for dark backgrounds.
- Overlay, focus, selection, and shadow tokens adjusted for dark mode.

This creates one component system with two palettes and prevents visual drift between modes.

### 3. Remove theme-specific hard-coded colors from component rules

Audit `src/index.css` for raw colors outside the theme declarations and replace them with semantic variables, including:

- Primary, destructive, and secondary button fills and borders.
- Sidebar hover and navigation selected states.
- Search fields, table headers, replay canvas surfaces, and filter bars.
- Critical incident washes, verification banners, containment summaries, and dialog overlays.
- Timeline markers, trust tracks, agent nodes, selected rows, and proof summaries.
- Text and icon colors that currently assume a dark background.

Introduce narrowly scoped tokens where necessary, such as:

- `--surface-inset`
- `--surface-overlay`
- `--selection`
- `--selection-strong`
- `--shadow-overlay`
- `--button-primary`
- `--button-primary-hover`
- `--table-header`
- `--backdrop`

No component should need to know which theme is active.

### 4. Rebalance the application shell for both themes

Keep the current compact sidebar and contextual top bar, but retune them so they work naturally in both modes:

- Give the sidebar enough contrast from the content canvas without turning light mode into a split black-and-white layout.
- Keep product identity restrained and reduce decorative framing around the logo.
- Make active navigation structurally clear through background, text, icon, and a narrow indigo indicator.
- Ensure inactive navigation remains readable in light mode.
- Use a lightly translucent/sticky top bar only where its backdrop remains legible in both modes; otherwise prefer an opaque semantic surface.
- Ensure production status, global search, notification controls, and user information have matching control states across themes.

No view-switching behavior or shell state will change.

### 5. Recalibrate shared components and data surfaces

Update shared visual patterns rather than styling each screen independently:

- Buttons: clear primary, secondary, ghost, and destructive hierarchy in both modes.
- Inputs/selects: visible boundaries, readable placeholder text, and accessible focus-visible states.
- Status indicators: maintain text plus dot semantics so color is not the only signal.
- Panels: use white/light surfaces and subtle borders in light mode, avoiding excessive card elevation.
- Tables: improve light-mode header separation, row hover, selected state, numeric alignment, and divider visibility.
- Inspectors: use grouped information and dividers instead of tinted nested cards.
- Toolbars and filters: distinguish controls from canvas without looking disabled.
- Dialogs: theme-aware backdrop, elevation, focus ring, and destructive action hierarchy.
- Code and hashes: maintain monospace clarity and sufficient contrast in both modes.

### 6. Tune every product view under both color schemes

#### Live Operations

- Preserve the operational summary, priority queue, activity table, selected-event inspector, agent posture, and mission state.
- Ensure the critical incident is prominent in light mode without using a large red fill.
- Make selected rows, paused state, and live/healthy states distinct in both themes.

#### Agents

- Preserve search, registry selection, trust data, detail workspace, and quarantine dialog.
- Tune neutral trust tracks and reserve red for genuinely low dimensions.
- Ensure capability chips and contract identifiers remain crisp rather than pill-heavy.

#### Incident Detail

- Maintain the evidence-first hierarchy and replay continuation.
- Retune critical timeline segments, policy violations, containment state, and trust impact so they remain readable without overwhelming the light canvas.

#### Forensic Replay

- Preserve event selection, autoplay, stepping, speed, scrubber, execution path, and state inspector.
- Make agent nodes and connectors feel like a technical analysis surface rather than presentation cards.
- Ensure selected/focused states remain obvious in both themes.

#### Audit Ledger

- Preserve row selection, evidence inspection, copy actions, and verification progress.
- Make chain summaries, verification progress, proof state, and long hashes legible on light surfaces.
- Ensure completed verification uses semantic green without washing the full workspace.

### 7. Responsive and system-preference handling

- Retain current desktop, laptop, tablet, and narrow breakpoints.
- Keep table horizontal scrolling where removing columns would lose operational meaning.
- Preserve logical stacked order for inspectors and multi-pane views.
- Verify that switching the operating system theme while the page is open updates automatically without reload or React state.
- Retain `prefers-reduced-motion` behavior independently from color scheme.
- Do not add theme transition animations, which can flash during OS-level changes and complicate reduced-motion expectations.

## File Scope

### `src/index.css`

Primary implementation file:

- Light-first semantic token palette.
- Dark-mode token overrides using `prefers-color-scheme`.
- Removal of theme-assuming hard-coded colors.
- Cross-theme tuning for shell, controls, tables, panels, views, dialog, and responsive states.

### `src/App.tsx`

Expected to require little or no structural change. Only adjust class hooks or semantics if a component currently cannot be styled correctly in both themes. Do not introduce JavaScript theme detection, a toggle, local storage, or duplicated themed markup.

### Unchanged

- `src/data.ts`
- `src/types.ts`
- Build and Vite configuration
- Dependencies and lockfile

## Edge Cases and Failure Modes

- Native select controls must remain readable in both system themes.
- Muted text must not become too faint on white surfaces or too bright in dark mode.
- Indigo primary buttons must meet text contrast requirements in both palettes.
- Semantic state backgrounds must remain distinguishable from row selection and hover states.
- Selected rows must not be confused with critical/error rows.
- Sticky top-bar transparency must not reduce legibility over scrolled content.
- Dialog backdrops and shadows must remain visible in light mode without looking heavy in dark mode.
- Long hashes, policy identifiers, and resource names must retain existing truncation and copying behavior.
- Browsers without `prefers-color-scheme` support will receive the default light theme.

## Behavior Preservation Checklist

- All five navigation destinations continue to render the intended view.
- Global and local input state remains unchanged.
- Operations filters and stream pause/resume continue to work.
- Event, agent, replay, and ledger selections continue to work.
- Incident-to-replay and event-to-ledger navigation remains intact.
- Replay controls and autoplay remain unchanged.
- Ledger verification still completes deterministically through five stages.
- Hash copy actions still copy complete values.
- Quarantine release still uses the confirmation dialog.

## Verification Strategy

1. Use the existing supervised preview; do not start another development server.
2. Inspect all five views with the device/browser preference set to light.
3. Inspect all five views with the preference set to dark.
4. Change the system preference while the app remains open and verify the theme updates automatically.
5. Check desktop, laptop, and narrow layouts in both modes.
6. Exercise hover, focus-visible, selected, disabled, destructive, progress, empty, and dialog states.
7. Confirm semantic state meaning remains clear without relying solely on color.
8. Audit changed CSS for theme-specific raw colors outside the token declarations.
9. Run `pnpm run build` and repair any introduced TypeScript, JSX, CSS, or Vite errors until it succeeds.

## Completion Criteria

- Light mode feels like the primary, deliberately designed enterprise experience rather than an inverted dark palette.
- Dark mode is an equally coherent counterpart using the same structural system.
- The active mode follows the device preference automatically with no user action.
- Both themes preserve clear hierarchy, balanced density, readable tables, and restrained semantic color.
- No component has duplicated light/dark markup or JavaScript theme branches.
- All existing interactions remain functional and the production build passes.
