(() => {
  "use strict";

  const tokens = Object.freeze({
    background: "#07110d",
    surface: "#0b1712",
    surface2: "#0e1d17",
    border: "#1e3229",
    text: "#edf7f1",
    muted: "#8fa39a",
    accent: "#78e6aa",
    accent2: "#52d98d",
    lime: "#c8f56b",
    warning: "#e5b85c",
    danger: "#ff7d7d",
  });

  window.PRISM_DESIGN_TOKENS = tokens;

  const replacements = new Map([
    ["#78e2c1", tokens.accent],
    ["#8ab4ff", tokens.lime],
    ["#9fb0c3", "#a9b5ae"],
    ["#1e2d40", tokens.border],
    ["rgba(120,226,193,.10)", "rgba(120,230,170,.12)"],
    ["rgba(120,226,193,0.10)", "rgba(120,230,170,.12)"],
  ]);

  function applyPalette(value, seen = new WeakSet()) {
    if (typeof value === "string") return replacements.get(value) || value;
    if (!value || typeof value !== "object") return value;
    if (seen.has(value)) return value;
    seen.add(value);

    if (Array.isArray(value)) {
      value.forEach((item, index) => { value[index] = applyPalette(item, seen); });
      return value;
    }

    Object.keys(value).forEach((key) => {
      value[key] = applyPalette(value[key], seen);
    });
    return value;
  }

  function finishLayout(layout = {}) {
    applyPalette(layout);
    layout.paper_bgcolor = "rgba(0,0,0,0)";
    layout.plot_bgcolor = "rgba(0,0,0,0)";
    layout.font = { ...(layout.font || {}), color: "#a9b5ae", family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' };

    ["xaxis", "yaxis"].forEach((axisName) => {
      const axis = layout[axisName] || {};
      layout[axisName] = {
        ...axis,
        gridcolor: tokens.border,
        zerolinecolor: tokens.border,
        linecolor: tokens.border,
        tickfont: { ...(axis.tickfont || {}), color: "#8fa39a" },
      };
    });
    return layout;
  }

  function patchPlotlyMethod(methodName) {
    if (!window.Plotly || typeof window.Plotly[methodName] !== "function") return;
    const original = window.Plotly[methodName].bind(window.Plotly);
    window.Plotly[methodName] = function themedPlotlyCall(graphDiv, data, layout, config, ...rest) {
      applyPalette(data);
      return original(graphDiv, data, finishLayout(layout || {}), config, ...rest);
    };
  }

  patchPlotlyMethod("newPlot");
  patchPlotlyMethod("react");
})();
