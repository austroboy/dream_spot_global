/* Dashboard interactions: sidebar, charts, kanban drag & drop */
(function () {
  "use strict";

  var toggle = document.querySelector(".dash-toggle");
  var side = document.querySelector(".dash__side");
  if (toggle && side) {
    toggle.addEventListener("click", function () { side.classList.toggle("is-open"); });
  }

  // Select-all checkbox for bulk actions
  var all = document.querySelector("[data-select-all]");
  if (all) {
    all.addEventListener("change", function () {
      document.querySelectorAll("input[name='selected']").forEach(function (cb) {
        cb.checked = all.checked;
      });
    });
  }

  // Charts (SRS FR-DSH-02)
  var mount = document.querySelector("[data-charts-url]");
  if (mount) {
    fetch(mount.dataset.chartsUrl)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var navy = "#123A73", gold = "#F2A526", blue = "#1877D2", navyLight = "#1E5099";
        draw("chartLeads", "line", d.by_day, navy, gold);
        draw("chartSource", "doughnut", d.by_source, null, null,
             [navy, gold, blue, "#1E9E6A", "#D64545", navyLight, "#5B6B85", "#0C2751"]);
        draw("chartCountry", "bar", d.by_country, gold, gold);
        draw("chartFunnel", "bar", d.funnel, navyLight, navyLight, null, true);
        draw("chartCounsellors", "bar", d.counsellors, navy, navy);
        draw("chartMonthly", "bar", d.monthly, gold, gold);
      })
      .catch(function () {});
  }

  function draw(id, type, data, border, fill, palette, horizontal) {
    var el = document.getElementById(id);
    if (!el || !data || !data.length) return;
    if (!window.Chart) { return drawFallback(el, type, data, palette, horizontal); }
    new window.Chart(el, {
      type: type,
      data: {
        labels: data.map(function (r) { return r.label; }),
        datasets: [{
          label: "Count",
          data: data.map(function (r) { return r.value; }),
          borderColor: border || "#123A73",
          backgroundColor: palette || (type === "line" ? "rgba(18,58,115,.10)" : fill),
          borderWidth: type === "line" ? 3 : 0,
          tension: 0.35,
          fill: type === "line",
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: horizontal ? "y" : "x",
        plugins: { legend: { display: type === "doughnut", position: "bottom" } },
        scales: type === "doughnut" ? {} : {
          y: { beginAtZero: true, grid: { color: "#E3E8EF" } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /* Dependency-free SVG fallback: the dashboard still renders every chart when the
     Chart.js CDN is unavailable (offline installs, restricted networks). */
  function drawFallback(canvas, type, data, palette, horizontal) {
    var NAVY = "#123A73", GOLD = "#F2A526";
    var colors = palette || [NAVY, GOLD, "#1877D2", "#1E9E6A", "#D64545", "#1E5099",
                             "#5B6B85", "#0C2751"];
    var w = canvas.parentElement.clientWidth || 520, h = 260;
    var max = Math.max.apply(null, data.map(function (d) { return d.value; })) || 1;
    var tilted = !horizontal && type !== "doughnut" && data.length > 5;
    var pad = { l: horizontal ? 130 : (tilted ? 52 : 40), r: 16, t: 14,
                b: tilted ? 62 : 46 };
    var iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
    var parts = ['<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" height="' + h +
                 '" font-family="Inter,sans-serif" font-size="11">'];

    if (type === "doughnut") {
      var total = data.reduce(function (a, d) { return a + d.value; }, 0) || 1;
      var legendH = 40;
      var cx = w / 2, cy = (h - legendH) / 2 + 4;
      var R = Math.min(cx, (h - legendH) / 2) - 8, r = R * 0.58, a0 = -Math.PI / 2;
      data.forEach(function (d, i) {
        var a1 = a0 + (d.value / total) * Math.PI * 2;
        var big = a1 - a0 > Math.PI ? 1 : 0;
        parts.push('<path d="M' + (cx + R * Math.cos(a0)) + ' ' + (cy + R * Math.sin(a0)) +
          ' A' + R + ' ' + R + ' 0 ' + big + ' 1 ' + (cx + R * Math.cos(a1)) + ' ' +
          (cy + R * Math.sin(a1)) + ' L' + (cx + r * Math.cos(a1)) + ' ' +
          (cy + r * Math.sin(a1)) + ' A' + r + ' ' + r + ' 0 ' + big + ' 0 ' +
          (cx + r * Math.cos(a0)) + ' ' + (cy + r * Math.sin(a0)) + ' Z" fill="' +
          colors[i % colors.length] + '"/>');
        a0 = a1;
      });
      data.slice(0, 4).forEach(function (d, i) {
        var y = h - 24 + (i % 2) * 13, x = 12 + Math.floor(i / 2) * (w / 2 - 4);
        parts.push('<rect x="' + x + '" y="' + (y - 8) + '" width="9" height="9" rx="2" fill="' +
          colors[i % colors.length] + '"/><text x="' + (x + 14) + '" y="' + y +
          '" font-size="10" fill="#5B6B85">' + esc(trunc(d.label, 16)) + ' (' + d.value +
          ')</text>');
      });
    } else if (horizontal) {
      var bh = Math.max(8, (ih / data.length) - 6);
      data.forEach(function (d, i) {
        var y = pad.t + i * (ih / data.length);
        var bw = (d.value / max) * iw;
        parts.push('<text x="' + (pad.l - 8) + '" y="' + (y + bh * 0.75) +
          '" text-anchor="end" fill="#5B6B85">' + esc(trunc(d.label, 22)) + '</text>' +
          '<rect x="' + pad.l + '" y="' + y + '" width="' + Math.max(bw, 1) + '" height="' + bh +
          '" rx="3" fill="' + NAVY + '"/><text x="' + (pad.l + bw + 6) + '" y="' +
          (y + bh * 0.78) + '" fill="#14213D">' + d.value + '</text>');
      });
    } else {
      parts.push('<line x1="' + pad.l + '" y1="' + (pad.t + ih) + '" x2="' + (w - pad.r) +
        '" y2="' + (pad.t + ih) + '" stroke="#E3E8EF"/>');
      var step = iw / data.length;
      if (type === "line") {
        var pts = data.map(function (d, i) {
          return (pad.l + step * i + step / 2) + "," + (pad.t + ih - (d.value / max) * ih);
        }).join(" ");
        parts.push('<polyline points="' + pts + '" fill="none" stroke="' + NAVY +
          '" stroke-width="3" stroke-linejoin="round"/>');
        data.forEach(function (d, i) {
          parts.push('<circle cx="' + (pad.l + step * i + step / 2) + '" cy="' +
            (pad.t + ih - (d.value / max) * ih) + '" r="3.5" fill="' + GOLD + '"/>');
        });
      } else {
        data.forEach(function (d, i) {
          var bw2 = Math.min(64, Math.max(6, step * 0.6)), bh2 = (d.value / max) * ih;
          parts.push('<rect x="' + (pad.l + step * i + (step - bw2) / 2) + '" y="' +
            (pad.t + ih - bh2) + '" width="' + bw2 + '" height="' + Math.max(bh2, 1) +
            '" rx="4" fill="' + (palette ? colors[i % colors.length] : NAVY) + '"/>');
        });
      }
      var every = Math.ceil(data.length / 9);
      var tilt = tilted;
      data.forEach(function (d, i) {
        if (i % every) return;
        var x = pad.l + step * i + step / 2, y = h - (tilt ? 40 : 26);
        parts.push('<text x="' + x + '" y="' + y + '" font-size="10" fill="#5B6B85" ' +
          (tilt ? 'text-anchor="end" transform="rotate(-32 ' + x + ' ' + y + ')"'
                : 'text-anchor="middle"') + '>' + esc(trunc(d.label, 14)) + '</text>');
      });
    }
    parts.push("</svg>");
    var box = document.createElement("div");
    box.innerHTML = parts.join("");
    canvas.replaceWith(box);
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function trunc(s, n) {
    s = String(s);
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  // Kanban drag and drop (SRS FR-LDM-08)
  var dragged = null;
  document.querySelectorAll(".kanban__card").forEach(function (card) {
    card.setAttribute("draggable", "true");
    card.addEventListener("dragstart", function () {
      dragged = card; card.classList.add("dragging");
    });
    card.addEventListener("dragend", function () {
      card.classList.remove("dragging"); dragged = null;
    });
  });
  document.querySelectorAll(".kanban__col").forEach(function (col) {
    col.addEventListener("dragover", function (e) {
      e.preventDefault(); col.classList.add("drop-target");
    });
    col.addEventListener("dragleave", function () { col.classList.remove("drop-target"); });
    col.addEventListener("drop", function (e) {
      e.preventDefault();
      col.classList.remove("drop-target");
      if (!dragged) return;
      col.querySelector(".kanban__list").appendChild(dragged);
      var body = new FormData();
      body.append("status", col.dataset.status);
      fetch(dragged.dataset.moveUrl, {
        method: "POST",
        headers: { "X-CSRFToken": window.dsgCookie ? window.dsgCookie("csrftoken") : "" },
        body: body,
      });
    });
  });
})();
