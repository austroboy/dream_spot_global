/* Dream Spot Global — progressive enhancement only (SRS CON-02) */
(function () {
  "use strict";

  // ---- Mobile navigation drawer -------------------------------------------
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".nav");
  var backdrop = document.querySelector(".nav-backdrop");
  var closeBtn = document.querySelector(".nav__close");
  var MOBILE = "(max-width: 1080px)";

  function isMobile() {
    return window.matchMedia(MOBILE).matches;
  }

  function openNav() {
    nav.classList.add("is-open");
    if (backdrop) backdrop.hidden = false;
    document.body.classList.add("nav-locked");
    toggle.setAttribute("aria-expanded", "true");
    if (closeBtn) closeBtn.focus();
  }

  function closeNav() {
    nav.classList.remove("is-open");
    if (backdrop) backdrop.hidden = true;
    document.body.classList.remove("nav-locked");
    toggle.setAttribute("aria-expanded", "false");
    nav.querySelectorAll(".nav__item.is-expanded").forEach(function (item) {
      item.classList.remove("is-expanded");
      var link = item.querySelector(".nav__link");
      if (link) link.setAttribute("aria-expanded", "false");
    });
  }

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      if (nav.classList.contains("is-open")) closeNav(); else openNav();
    });
    if (closeBtn) closeBtn.addEventListener("click", closeNav);
    if (backdrop) backdrop.addEventListener("click", closeNav);

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        closeNav();
        toggle.focus();
      }
    });

    // Tapping a real link closes the drawer so the next page is not covered.
    // Top-level links that own a submenu are accordion toggles, not navigation.
    nav.querySelectorAll("a[href]").forEach(function (link) {
      link.addEventListener("click", function () {
        if (!isMobile()) return;
        var item = link.closest(".nav__item");
        var isAccordionToggle = link.classList.contains("nav__link") &&
                                item && item.querySelector(".megamenu");
        if (isAccordionToggle) return;
        closeNav();
      });
    });

    // Top-level items with a submenu become accordions on mobile
    nav.querySelectorAll(".nav__item").forEach(function (item) {
      var link = item.querySelector(".nav__link");
      var submenu = item.querySelector(".megamenu");
      if (!link || !submenu) return;
      link.setAttribute("aria-expanded", "false");
      link.addEventListener("click", function (e) {
        if (!isMobile()) return;          // desktop keeps hover menus
        e.preventDefault();
        e.stopPropagation();
        var expanded = item.classList.toggle("is-expanded");
        link.setAttribute("aria-expanded", expanded ? "true" : "false");
      });
    });

    // Never leave the drawer stuck open when rotating to a wide screen
    window.addEventListener("resize", function () {
      if (!isMobile() && nav.classList.contains("is-open")) closeNav();
    });
  }

  // Accordions (FAQ)
  document.querySelectorAll(".accordion__trigger").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var item = btn.closest(".accordion__item");
      var isOpen = item.classList.contains("is-open");
      item.classList.toggle("is-open", !isOpen);
      btn.setAttribute("aria-expanded", !isOpen ? "true" : "false");
    });
  });

  // Reveal on scroll + counter animation (SRS FR-HOM-05, UI-09)
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var observer = "IntersectionObserver" in window
    ? new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          if (entry.target.dataset.count && !reduce) countUp(entry.target);
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.15 })
    : null;
  document.querySelectorAll(".reveal, [data-count]").forEach(function (el) {
    if (observer) { observer.observe(el); } else { el.classList.add("is-visible"); }
  });

  function countUp(el) {
    var raw = el.dataset.count || "";
    var target = parseFloat(raw.replace(/[^0-9.]/g, ""));
    if (isNaN(target)) return;
    var suffix = raw.replace(/[0-9.,]/g, "");
    var start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / 1100, 1);
      var value = Math.floor(target * p);
      el.textContent = value.toLocaleString() + suffix;
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = raw;
    }
    requestAnimationFrame(step);
  }

  // Auto-dismiss alerts
  document.querySelectorAll(".alert").forEach(function (a) {
    setTimeout(function () { a.style.opacity = "0"; }, 6000);
    setTimeout(function () { a.remove(); }, 6600);
  });

  // Shortlist toggle
  document.querySelectorAll("[data-shortlist]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      fetch(btn.dataset.shortlist, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken"), "x-requested-with": "fetch" },
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          btn.classList.toggle("chip--active", d.added);
          btn.textContent = d.added ? "★ Shortlisted" : "☆ Shortlist";
        })
        .catch(function () {});
    });
  });

  // Confirmation modals for destructive actions (SRS UI-11)
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.dataset.confirm)) e.preventDefault();
    });
  });

  // Slot picker on the booking page
  document.querySelectorAll("[data-slot]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("[data-slot]").forEach(function (b) {
        b.classList.remove("chip--active");
      });
      btn.classList.add("chip--active");
      var input = document.querySelector("#id_slot");
      if (input) input.value = btn.dataset.slot;
      var summary = document.querySelector("#slot-summary");
      if (summary) summary.textContent = btn.dataset.label || btn.textContent.trim();
    });
  });

  // Day tabs on the booking calendar
  document.querySelectorAll("[data-day]").forEach(function (tab) {
    tab.addEventListener("click", function (e) {
      e.preventDefault();
      document.querySelectorAll("[data-day]").forEach(function (t) {
        t.classList.remove("is-active");
      });
      tab.classList.add("is-active");
      document.querySelectorAll("[data-day-panel]").forEach(function (p) {
        p.classList.toggle("hide", p.dataset.dayPanel !== tab.dataset.day);
      });
    });
  });

  function getCookie(name) {
    var v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }
  window.dsgCookie = getCookie;
})();
