# Clarisal Brand Tech Design Guidelines

## Purpose

This document defines the visual, interaction, and implementation standards for Clarisal's frontend. It is intended to keep Control Tower, organisation admin, and employee self-service surfaces coherent as the product expands.

Clarisal is an enterprise workforce platform. The design language must feel operationally sharp, credible, calm under pressure, and premium without becoming decorative or soft.

## Brand Principles

1. Build trust first.
Clarisal handles employee records, onboarding state, licences, and payroll-adjacent data. Visuals must communicate control, precision, and stability.

2. Separate power from noise.
The UI should feel rich, but density must never make workflows harder to scan. Important actions should be visually obvious, not visually loud.

3. Distinguish surfaces by intent.
Auth pages can be expressive. Application workspaces should be more restrained, denser, and more efficient.

4. Design for multi-role work.
Control Tower, org admin, and employee flows live in one product. The system should feel unified while still giving each audience a distinct operating context.

5. Loading is part of the product.
Blank states and generic spinners are not acceptable defaults. Skeletons should preserve structure and reduce uncertainty.

## Visual Direction

### Overall Style

- Primary product style: executive enterprise with dimensional layering.
- Supporting influences: soft UI evolution, executive dashboard, trust-and-authority patterns.
- Avoid: generic startup gradients, purple-heavy "AI SaaS" styling, over-rounded toy-like controls, neon dashboard aesthetics.

### Workspace Character

- Workforce auth:
  Clean, high-polish, more expressive, more atmospheric, slightly editorial.

- Control Tower:
  Command-surface feel with darker framing, stronger contrast, and clearer operational status emphasis.

- Organisation admin:
  Efficient people-operations workspace with dense but calm CRUD/table behavior.

- Employee self-service:
  Guidance-oriented workspace with clear progress, approachable sectioning, and less visual pressure.

## Typography

### Font Stack

- UI and headings: `Plus Jakarta Sans`
- Data, codes, and system metadata: `JetBrains Mono`

### Usage Rules

- Large headings should feel compact and decisive, not airy.
- Tables, badges, employee codes, and audit metadata should use tighter rhythm and clearer contrast.
- Avoid overly light font weights for key operational text.

## Color System

### Light Theme Tokens

- Canvas: `#F8FAFC`
- Canvas secondary: `#EEF4FB`
- Surface: `#FFFFFF`
- Elevated surface: `#F8FBFF`
- Surface subtle: `#EEF3F8`
- Foreground: `#0F172A`
- Strong foreground: `#0B1220`
- Muted text: `#64748B`
- Brand: `#1E40AF`
- Brand strong: `#3563FF`
- Accent: `#D97706`
- Success: `#059669`
- Warning: `#D97706`
- Destructive: `#DC2626`
- Info: `#2563EB`
- Border: `#E2E8F0`

### Dark Theme Tokens

- Canvas: `#020617`
- Canvas secondary: `#0A1221`
- Surface: `#10182A`
- Elevated surface: `#131D31`
- Surface subtle: `#1A2438`
- Foreground: `#F8FAFC`
- Strong foreground: `#FFFFFF`
- Muted text: `#94A3B8`
- Brand: `#60A5FA`
- Brand strong: `#7BB2FF`
- Accent: `#F59E0B`
- Success: `#34D399`
- Warning: `#FBBF24`
- Destructive: `#F87171`
- Info: `#60A5FA`
- Border: `#334155`

### Semantic Usage

- Brand is for primary CTAs, active emphasis, selection, and important progress indicators.
- Success is for verified, active, completed, or healthy states.
- Warning is for pending action, seat pressure, and cautionary status.
- Destructive is for suspend, reject, terminate, or error states.
- Info is for onboarding progress and non-destructive operational status.

## Layout System

### Shell Rules

- Max application width: `1500px`
- Use large, soft-rectangular surfaces for major containers.
- Prefer surface stacking over heavy borders everywhere.
- Keep topbars visually lighter than sidebars so content remains the focal plane.

### Spacing

- Page section rhythm: `24px`
- Card padding:
  - Standard: `20px`
  - Large: `24px`
- Table row vertical padding: `16px`

### Radius

- Buttons and inputs: `16px` to `22px`
- Cards and section panels: `24px` to `30px`
- Status pills: fully rounded

## Motion System

### Approved Motion Tools

- Use `motion` for JavaScript-driven animation orchestration.
- Use CSS/Tailwind transitions for hover, focus, and simple press states.
- Do not add legacy `framer-motion` alongside `motion`.

### Motion Intensity

- Auth pages:
  Richer motion, staggered entrance, layered backgrounds, animated metric chips.

- Dashboards:
  Subtle page enter, card rise, soft opacity transitions.

- CRUD pages:
  Restraint first. Motion should support orientation, not become attention-seeking.

### Timing

- Micro interactions: `140ms` to `180ms`
- Standard transitions: `180ms` to `240ms`
- Larger route or section transitions: `220ms` to `320ms`

### Reduced Motion

- Respect `prefers-reduced-motion` everywhere.
- Replace large transforms with opacity-only or instant transitions where needed.
- Never make completion of a task depend on animation finishing.

## Component Standards

### Buttons

- Primary buttons should feel confident and highly legible.
- Secondary buttons should stay visible in both themes without becoming filled-primary lookalikes.
- Danger buttons should be reserved for irreversible or high-risk actions only.

### Inputs

- Inputs must use semantic surface and ring tokens, not hardcoded grayscale values.
- Validation messages should be direct and task-oriented.
- Required fields should only use destructive color for the required mark, not for the full label.

### Tables

- Tables should use a dedicated shell with consistent header rhythm and hover feedback.
- Status columns should rely on badges rather than plain text where possible.
- Secondary metadata must be visually subordinate to primary row identity.

### Cards

- Metric cards should use subtle motion and clear icon containers.
- Detail cards should prioritize readability and strong label/value hierarchy.

### Empty States

- Every empty state must explain why it is empty and what action is next.
- Empty states should not feel like errors unless the system is actually in failure.

### Status Badges

- Use uppercase, compact pills for clarity.
- Keep colors semantic and consistent across roles and pages.
- Never overload one color across unrelated state types.

## Role-Specific Patterns

### Control Tower

- Darker shell, stronger contrast, more command-center tone.
- Promote lifecycle, billing, licence, and access-state information visually.
- Organisation detail pages should make activation blockers obvious within one viewport.

### Organisation Admin

- Lists, filters, and detail views should feel efficient and calm.
- Master data screens should support repetition without fatigue.
- Employee pages should keep assignment, status, and documents tightly connected.

### Employee Self-Service

- Show progress clearly.
- Group profile, IDs, bank, education, and documents into understandable chunks.
- Reduce intimidation around sensitive inputs with supportive microcopy and structured sections.

## Skeleton Loading Standards

### General Rule

If the page layout is known, render a layout-matched skeleton instead of a spinner.

### Required Skeleton Coverage

- Auth bootstrap and token validation
- Control Tower dashboard and organisations list/detail
- Organisation dashboard
- Locations, departments, employees list/detail
- Employee dashboard
- Employee profile, education, and documents

### Skeleton Patterns

- Metric cards: placeholder title, value, icon block
- Tables: row-level shells matching table rhythm
- Forms: label + input field pairs in real layout proportions
- Topbars and page headers: preserve action placement so pages do not jump on load

### Avoid

- Full-page centered spinner as default
- Skeletons that do not resemble final layout
- Long loading states with no sense of what is coming

## Accessibility Checklist

- Meet WCAG AA contrast in both themes.
- Preserve visible focus rings on all interactive elements.
- Ensure keyboard access for theme switching, dropdowns, dialogs, and tables.
- Keep status color paired with text, not color alone.
- Ensure light and dark themes are both production-ready, not inverse hacks.

## Responsive Baseline

Validate all major surfaces at:

- `375px`
- `768px`
- `1024px`
- `1440px`

Desktop-first is acceptable for admin-heavy pages, but responsive behavior must still preserve readability and action discoverability.

## Implementation Rules

- Use semantic CSS variables instead of hardcoded page-level colors.
- Reuse shared primitives before creating page-specific one-off styles.
- Prefer composition of `PageHeader`, `SectionCard`, `MetricCard`, `EmptyState`, `StatusBadge`, and skeleton primitives.
- All new async pages should include skeleton states as part of the initial implementation.

## Review Bar

A page is not done until it satisfies all of the following:

- Works in light and dark mode
- Has intentional loading, empty, success, and error states
- Preserves keyboard and focus usability
- Uses semantic tokens instead of ad hoc colors
- Feels like Clarisal, not a generic admin template
