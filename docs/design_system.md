# PRISM Design System

PRISM uses a restrained enterprise visual language designed for reporting, analytics, strategy and governance work. The interface should feel calm, precise and business-oriented rather than decorative or consumer-oriented.

## Canonical dark palette

| Token | Value | Use |
| --- | --- | --- |
| Canvas | `#0B1220` | Application background |
| Sidebar | `#0F172A` | Navigation / utility rail |
| Surface | `#111827` | Primary cards and panels |
| Surface 2 | `#172033` | Elevated controls and table headers |
| Border | `#263247` | Dividers, card and input borders |
| Text | `#F8FAFC` | Primary content |
| Muted | `#94A3B8` | Secondary labels and metadata |
| Soft text | `#CBD5E1` | Body/supporting copy |
| Cobalt | `#60A5FA` | Primary interaction/accent |
| Blue | `#3B82F6` | Strong analytical emphasis |
| Action blue | `#2563EB` | Primary action depth |
| Soft blue | `#93C5FD` | Brand/highlight support |
| Success | `#2DD4BF` | Positive/success state only |
| Warning | `#F59E0B` | Warning state |
| Danger | `#F87171` | Error/high-risk state |

## Visual principles

1. **Professional and restrained.** Navy/slate neutrals dominate; accent colour is used to guide attention, not decorate large surfaces.
2. **Clear hierarchy before effects.** Typography, spacing, borders and data density carry the design. Blur/shadow are subtle supporting treatments.
3. **Cobalt carries interaction.** Active navigation, links, focus states and analytical emphasis use the blue family.
4. **Semantic colour stays semantic.** Teal is reserved for positive/success states, amber for warning, red for danger/risk.
5. **No lime/green brand wash.** The previous green/lime-heavy identity is deprecated for PRISM.
6. **Compact enterprise geometry.** Cards generally use 10–14 px corner radii; pills are reserved for status/tags.
7. **Quiet typography.** Inter/system UI stacks, strong hierarchy, restrained heading tracking and muted secondary copy.
8. **Charts inherit the enterprise palette.** Use cobalt/sky/slate series by default; semantic warning/danger colours appear only when the data meaning requires them.
9. **Accessibility is a release gate.** Focus visibility and contrast must remain strong across desktop/mobile; serious/critical axe violations block release.

## Implementation

- `assets/styles.css` is the canonical browser-native design-token source.
- `assets/mobile.css` extends those tokens into the mobile shell.
- `assets/compact-metrics.css` uses the same palette for compact KPI/semantic layouts.
- `assets/app.js` applies the chart/notice palette.
- `.github/workflows/browser-e2e.yml` verifies canonical palette tokens and runs Chromium/axe acceptance tests.
- `index.html` uses `#0B1220` as the browser theme colour and versioned stylesheet URLs to avoid stale cached themes.

When adding a new PRISM component, reuse these semantic tokens before introducing a new colour or visual pattern.
