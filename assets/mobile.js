(() => {
  "use strict";

  const MOBILE_BREAKPOINT = 820;
  const SIDEBAR_IDLE_CLOSE_MS = 6500;

  document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");
    const introToggle = document.getElementById("introToggle");
    const introDetails = document.getElementById("introDetails");

    if (!sidebar || !menuToggle || !sidebarBackdrop || !introToggle || !introDetails) return;

    let sidebarTimer = null;
    const isMobile = () => window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`).matches;

    function clearSidebarTimer() {
      if (sidebarTimer) window.clearTimeout(sidebarTimer);
      sidebarTimer = null;
    }

    function scheduleSidebarClose() {
      clearSidebarTimer();
      if (!isMobile() || !body.classList.contains("sidebar-open")) return;
      sidebarTimer = window.setTimeout(() => closeSidebar({ restoreFocus: false }), SIDEBAR_IDLE_CLOSE_MS);
    }

    function openSidebar() {
      if (!isMobile()) return;
      body.classList.add("sidebar-open");
      sidebar.setAttribute("aria-hidden", "false");
      menuToggle.setAttribute("aria-expanded", "true");
      menuToggle.setAttribute("aria-label", "Close navigation");
      scheduleSidebarClose();
    }

    function closeSidebar({ restoreFocus = false } = {}) {
      clearSidebarTimer();
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
    }

    function syncLayout() {
      if (isMobile()) {
        closeSidebar();
        setIntro(false);
        sidebar.setAttribute("aria-hidden", "true");
      } else {
        clearSidebarTimer();
        body.classList.remove("sidebar-open");
        sidebar.removeAttribute("aria-hidden");
        menuToggle.setAttribute("aria-expanded", "false");
        setIntro(true);
      }
    }

    menuToggle.addEventListener("click", toggleSidebar);
    sidebarBackdrop.addEventListener("click", () => closeSidebar({ restoreFocus: true }));
    introToggle.addEventListener("click", () => setIntro(!introDetails.classList.contains("is-open")));

    sidebar.addEventListener("pointerdown", scheduleSidebarClose);
    sidebar.addEventListener("focusin", scheduleSidebarClose);
    sidebar.addEventListener("scroll", scheduleSidebarClose, { passive: true });

    document.querySelectorAll(".nav-item").forEach((button) => {
      button.addEventListener("click", () => {
        if (isMobile()) closeSidebar();
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

    let resizeTimer = null;
    window.addEventListener("resize", () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(syncLayout, 120);
    });

    syncLayout();
  });
})();
