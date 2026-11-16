# PRISM Design System

PRISM uses a dark, business-oriented visual system with a controlled multi-accent palette. The design should feel serious enough for enterprise reporting and strategy work, while still being memorable, energetic and easy to scan.

The principle is **neutral workspace + purposeful colour**. Large surfaces remain graphite/charcoal; colour is reserved for navigation cues, KPI identity, charts, semantic states and high-value actions.

## Canonical dark palette

### Foundation

| Token | Value | Use |
| --- | --- | --- |
| Canvas | `#121217` | Application background |
| Sidebar | `#17171E` | Navigation / utility rail |
| Surface | `#1D1D26` | Primary cards and panels |
| Surface 2 | `#242431` | Elevated controls / table headers |
| Surface 3 | `#16161D` | Deep inputs / recessed areas |
| Border | `#353545` | Dividers, card and input borders |
| Text | `#F8F7FB` | Primary content |
| Muted | `#A7A5B3` | Secondary labels and metadata |
| Soft text | `#D7D5DE` | Supporting content |

### Brand and information accents

| Token | Value | Use |
| --- | --- | --- |
| Orchid | `#A78BFA` | Primary PRISM accent, focus, primary analytical emphasis |
| Deep violet | `#7C3AED` | Primary action depth |
| Coral | `#FF786B` | Secondary brand accent, category/group contrast |
| Mint | `#3DD6A5` | Positive/success state and one chart family |
| Amber | `#F6C453` | Attention, warning/highlight and one chart family |
| Rose | `#F472B6` | Tertiary/category accent |
| Plum | `#C084FC` | Additional analytical/category accent |
| Danger | `#FF5D73` | Error/high-risk state |

## Visual principles

1. **No single-colour wash.** PRISM should not read as “the blue app” or “the green app.”
2. **Neutral surfaces dominate.** Graphite and charcoal provide a stable analytical canvas.
3. **Colour has a job.** Orchid, coral, mint, amber, rose and plum identify categories, metrics, chart series and states.
4. **Primary actions stay coherent.** Deep violet/magenta carries the highest-priority action treatment instead of rotating button colours.
5. **Status colours remain semantic.** Mint means positive/success, amber means attention/warning and danger red is reserved for risk/error.
6. **Multi-colour accents stay small.** KPI top rules, nav dots, chart series and brand marks can be colourful; large card backgrounds remain neutral.
7. **Charts use the shared six-colour sequence.** Orchid → Coral → Mint → Amber → Rose → Plum.
8. **Compact enterprise geometry.** Cards generally use 10–14 px corner radii; pills are for statuses/tags.
9. **Accessibility is a release gate.** Colour is never the only signal; focus visibility and contrast must remain strong on desktop/mobile.

## Component behaviour

### Navigation
Each analytical view receives a small colour cue. The active view uses that cue on its edge while retaining a neutral/tinted background.

### KPI cards
Metric cards use a 2 px coloured top rule. Repeating metric grids cycle through the six accent colours rather than tinting the whole card.

### Charts
Charts use the common six-colour palette. Forecast confidence areas use transparent orchid while actual values remain neutral so projected data is visually distinct.

### Brand mark
The PRISM mark uses an amber → coral → rose → orchid gradient with a mint inner detail. It is the most colourful single element in the shell.

## Implementation

- `assets/styles.css` is the canonical browser design-token source.
- `assets/mobile.css` inherits the same palette for mobile surfaces.
- `assets/compact-metrics.css` retains the same semantic colours at phone widths.
- `assets/theme.js` exposes `PRISM_DESIGN_TOKENS` and the chart palette.
- `assets/app.js` applies the chart and notice palette.
- `assets/prism.svg` carries the multi-colour brand treatment.
- `.github/workflows/browser-e2e.yml` verifies the no-blue palette contract and runs Chromium/axe acceptance tests.
- `index.html` and `manifest.webmanifest` use `#121217` as the browser/PWA theme colour.

When adding a new component, reuse one of these semantic colours before introducing another hue.
