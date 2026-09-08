(() => {
  "use strict";

  const MOBILE_BREAKPOINT = 820;

  document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");
    const introToggle = document.getElementById("introToggle");
    const introDetails = document.getElementById("introDetails");

    if (!sidebar || !menuToggle || !sidebarBackdrop || !introToggle || !introDetails) return;

    const isMobile = () => window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`).matches;
    const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let lastMobileState = isMobile();
    let layoutTimer = null;
    let chartTimer = null;

    function resizeCharts() {
      if (!window.Plotly || !window.Plotly.Plots) return;
      document.querySelectorAll(".chart .js-plotly-plot").forEach((plot) => {
        if (plot.offsetParent !== null) {
          try {
            window.Plotly.Plots.resize(plot);
          } catch (_) {
            // Plotly may still be initialising; the app's responsive config remains the fallback.
          }
        }
      });
    }

    function scheduleChartResize(delay = 80) {
      window.clearTimeout(chartTimer);
      chartTimer = window.setTimeout(resizeCharts, delay);
    }

    function openSidebar() {
      if (!isMobile()) return;
      body.classList.add("sidebar-open");
      sidebar.setAttribute("aria-hidden", "false");
      menuToggle.setAttribute("aria-expanded", "true");
      menuToggle.setAttribute("aria-label", "Close navigation");
    }

    function closeSidebar({ restoreFocus = false } = {}) {
      body.classList.remove("sidebar-open");
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Open navigation");
      if (isMobile()) sidebar.setAttribute("aria-hidden", "true");
      else sidebar.removeAttribute("aria-hidden");
      if (restoreFocus && isMobile()) menuToggle.focus();
    }

    function toggleSidebar() {
      if (body.classList.contains("sidebar-open")) closeSidebar({ restoreFocus: true });
      else openSidebar();
    }

    function setIntro(open) {
      introDetails.classList.toggle("is-open", open);
      introToggle.setAttribute("aria-expanded", String(open));
      introToggle.setAttribute("aria-label", open ? "Hide introduction" : "Show introduction");
      scheduleChartResize(220);
    }

    function scrollViewToTop() {
      if (!isMobile()) return;
      window.scrollTo({ top: 0, behavior: reduceMotion() ? "auto" : "smooth" });
    }

    function syncLayout(force = false) {
      const mobile = isMobile();
      if (!force && mobile === lastMobileState) {
        scheduleChartResize();
        return;
      }

      lastMobileState = mobile;
      if (mobile) {
        closeSidebar();
        setIntro(false);
        sidebar.setAttribute("aria-hidden", "true");
      } else {
        body.classList.remove("sidebar-open");
        sidebar.removeAttribute("aria-hidden");
        menuToggle.setAttribute("aria-expanded", "false");
        setIntro(true);
      }
      scheduleChartResize(120);
    }

    menuToggle.addEventListener("click", toggleSidebar);
    sidebarBackdrop.addEventListener("click", () => closeSidebar({ restoreFocus: true }));
    introToggle.addEventListener("click", () => setIntro(!introDetails.classList.contains("is-open")));

    document.querySelectorAll(".nav-item").forEach((button) => {
      button.addEventListener("click", () => {
        if (isMobile()) {
          closeSidebar();
          scrollViewToTop();
          scheduleChartResize(140);
        }
      });
    });

    const fileInput = document.getElementById("fileInput");
    if (fileInput) fileInput.addEventListener("change", () => {
      if (isMobile()) closeSidebar();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        if (body.classList.contains("sidebar-open")) closeSidebar({ restoreFocus: true });
        else if (isMobile() && introDetails.classList.contains("is-open")) setIntro(false);
      }
    });

    window.addEventListener("resize", () => {
      window.clearTimeout(layoutTimer);
      layoutTimer = window.setTimeout(() => syncLayout(false), 120);
    });

    window.addEventListener("orientationchange", () => {
      closeSidebar();
      window.setTimeout(() => {
        lastMobileState = isMobile();
        scheduleChartResize(120);
      }, 180);
    });

    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", () => scheduleChartResize(120));
    }

    syncLayout(true);
  });
})();
