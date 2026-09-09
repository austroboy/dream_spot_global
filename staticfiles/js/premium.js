/* Premium layer: staggered reveals, hero parallax, marquee duplication.
   Progressive enhancement only — the page is fully usable without it. */
(function () {
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Stagger reveals within each grid so cards cascade instead of popping together
  document.querySelectorAll(".grid, .stats, .steps").forEach(function (group) {
    var items = group.querySelectorAll(".reveal");
    items.forEach(function (el, i) {
      el.style.transitionDelay = Math.min(i * 70, 420) + "ms";
    });
  });

  // Seamless marquee: duplicate the track content so the loop has no gap
  var track = document.querySelector(".marquee__track");
  if (track && !reduce) {
    track.innerHTML += track.innerHTML;
  }

  // Subtle pointer parallax on the hero composition
  var visual = document.querySelector(".hero__visual");
  if (visual && !reduce && window.matchMedia("(pointer: fine)").matches) {
    var hero = document.querySelector(".hero");
    hero.addEventListener("mousemove", function (e) {
      var r = hero.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      visual.querySelectorAll(".float-card").forEach(function (card, i) {
        var depth = 14 + i * 7;
        card.style.transform = "translate(" + x * depth + "px," + y * depth + "px)";
      });
      var globe = visual.querySelector(".globe");
      if (globe) globe.style.transform = "translate(" + x * 8 + "px," + y * 8 + "px)";
    });
    hero.addEventListener("mouseleave", function () {
      visual.querySelectorAll(".float-card, .globe").forEach(function (el) {
        el.style.transform = "";
      });
    });
  }
})();
