# PRISM Design System

PRISM uses a deep green enterprise visual system designed for reporting, analytics, strategy and governance work. The interface should feel calm, premium and data-oriented, with colour concentrated in interaction, status, charts and analytical emphasis.

## Canonical green palette

| Token | Value | Use |
| --- | --- | --- |
| Canvas | `#07110D` | Application background |
| Sidebar | `#09140F` | Navigation / utility rail |
| Surface | `#0B1712` | Primary cards and panels |
| Surface 2 | `#0E1D17` | Elevated controls / table headers |
| Surface 3 | `#091510` | Deep inputs / recessed areas |
| Border | `#1E3229` | Dividers and input/card borders |
| Primary text | `#EDF7F1` | Main content |
| Muted text | `#8FA39A` | Secondary labels |
| Soft text | `#C9D8D0` | Supporting copy |
| Mint | `#78E6AA` | Primary interaction/accent |
| Emerald | `#52D98D` | Secondary analytical accent |
| Deep green | `#31B76E` | Primary action depth |
| Lime | `#C8F56B` | Highlight / high-attention accent |
| Soft mint | `#93F2C5` | Positive analytical series |
| Mid green | `#69D99E` | Additional chart/category accent |
| Yellow-green | `#A6E878` | Additional chart/category accent |
| Warning | `#E5B85C` | Warning state |
| Danger | `#FF7D7D` | Error / risk state |

## Visual principles

1. **Green is the primary identity.** PRISM should read as one coherent green enterprise product.
2. **Dark surfaces stay dominant.** Mint/lime accents guide the eye without flooding the interface.
3. **Green shades carry analytical variety.** KPI rules and charts cycle through mint, emerald, soft mint, lime, mid green and yellow-green.
4. **Primary actions stay consistent.** Use deep green → emerald for high-priority actions.
5. **Semantic colour remains explicit.** Amber is warning; red is danger.
6. **Compact enterprise geometry.** Cards generally use 10–14 px radii; pills remain for tags/statuses.
7. **Accessibility remains a release gate.** Colour is never the only signal and desktop/mobile contrast must remain strong.

## Implementation

- `assets/styles.css` is the canonical browser token source.
- `assets/mobile.css` inherits the green shell.
- `assets/compact-metrics.css` preserves the green KPI treatment on phones.
- `assets/theme.js` exposes the green design tokens and chart palette.
- `assets/app.js` uses the green analytical sequence.
- `assets/prism.svg` uses lime → mint → emerald.
- `.github/workflows/browser-e2e.yml` validates the green palette contract before Chromium/axe.
- `index.html` and `manifest.webmanifest` use `#07110D` for browser/PWA theme colour.
