# PRISM Design System

PRISM belongs to the same product family as **The Palm**, **NEXUS**, XPLORE and related portfolio applications. Its interface should feel like a specialised enterprise product in that family, not a separate visual brand.

## Canonical dark palette

| Token | Value | Use |
| --- | --- | --- |
| Background | `#07110d` | Application canvas |
| Surface | `#0b1712` | Primary cards/panels |
| Surface 2 | `#0e1d17` | Elevated controls/table headers |
| Border | `#1e3229` | Dividers, panel and input borders |
| Text | `#edf7f1` | Primary content |
| Muted | `#8fa39a` | Secondary labels and metadata |
| Green | `#78e6aa` | Primary accent, active state, links |
| Green 2 | `#52d98d` | Secondary accent and chart support |
| Lime | `#c8f56b` | High-emphasis accent and primary gradients |
| Warning | `#e5b85c` | Warning state |
| Danger | `#ff7d7d` | Error/high-risk state |

## Visual principles

1. **Dark-first and restrained.** Use the green-black canvas and avoid large saturated colour fields.
2. **Enterprise glass, not decorative glass.** Panels may use slight transparency, blur and soft shadow, but readability and data density come first.
3. **Green carries interaction.** Active navigation, links, focus states and analytical emphasis use the shared green family.
4. **Lime is scarce.** Reserve lime for the brand mark, important primary actions and selected high-value emphasis.
5. **No competing blue product theme.** Blue may appear only as a very subtle ambient tone or when semantically required by a data visualisation.
6. **Compact rounded geometry.** Enterprise cards generally use 10–14 px corner radii; pills are reserved for status/tags.
7. **Typography is quiet.** Use Inter/system UI stacks, strong hierarchy, negative heading tracking and muted secondary copy.
8. **Charts follow the product palette.** Forecasts, segment charts and future visualisations should use the shared green/lime palette unless the data semantics require warning/danger colours.

## Implementation

- `assets/styles.css` is the canonical browser-native design token source.
- `assets/theme.js` maps Plotly output into the shared palette.
- `assets/prism.svg` uses the same green/lime brand family.
- `.streamlit/config.toml` and `prism/ui/theme.py` keep the retained Streamlit reference implementation visually aligned.
- CI verifies the canonical background, green and lime tokens and checks the chart-theme JavaScript syntax.

When adding a new PRISM component, reuse these tokens before introducing a new colour or visual pattern.
