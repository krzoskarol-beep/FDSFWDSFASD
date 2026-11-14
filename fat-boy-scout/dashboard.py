"""Panel HTML Fat Boy Scout: kafelki z liczbami, wykres cena–przebieg i tabela wszystkich ofert z linkami.

Jeden samodzielny plik (bez zewnętrznych skryptów i czcionek) – otwiera się w telefonie z repozytorium
albo po pobraniu. Dane te same co w raporcie tekstowym (scout.report_sets).
Paleta: dwa pierwsze sloty palety referencyjnej skilla dataviz, sprawdzone walidatorem (jasny i ciemny,
wszystkie pary) – niebieski = potwierdzone, pomarańczowy = do sprawdzenia; dodatkowo różny kształt znacznika.
"""
from __future__ import annotations

import html
import json

import scout


def _row(l: dict, kind: str, sets: dict, config: dict) -> dict:
    known, missing = scout.missing_info(l, config)
    dist, _ = scout.distance_of(l)
    tot = scout.total_cost(l, config)
    tags = []
    if l["id"] in sets["new_ids"]:
        tags.append("NOWA")
    if l["id"] in sets["drop_ids"]:
        tags.append("TANIEJ")
    if l.get("relist"):
        tags.append("PONOWNIE")
    return {
        "id": l["id"], "kind": kind, "model": l.get("model") or "Fat Boy", "year": l.get("year"),
        "price": l.get("price"), "miles": l.get("miles"), "loc": scout._loc(l), "state": l.get("state"),
        "dist": round(dist) if dist is not None else None, "total": round(tot) if tot is not None else None,
        "url": l.get("url"), "direct": scout.is_direct_link(l.get("url"), l), "title": l.get("title"),
        "missing": missing, "tags": tags, "old_price": l.get("old_price"),
        "change": scout.change_line(l, config) or None, "dup_of": l.get("dup_of"),
    }


def build_rows(sets: dict, config: dict) -> list[dict]:
    rows = [_row(l, "ok", sets, config) for l in sets["confirmed"]]
    rows += [_row(l, "check", sets, config) for l in sets["to_check"] + sets["watch"]]
    return rows


def build_html(sets: dict, run: dict, config: dict, report_no: int) -> str:
    rows = build_rows(sets, config)
    meta = {
        "title": f"Fat Boy Scout – raport nr {report_no}",
        "date": scout.pl_date(run["date"]), "run_id": run.get("run_id", run["date"]),
        "max_price": config["max_price_usd"],
        "max_miles": (config.get("categories", {}).get("main", {}) or {}).get("max_miles"),
    }
    data = json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__TITLE__", html.escape(meta["title"])).replace("__DATA__", data)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
.viz-root {
  color-scheme: light;
  --page: #f9f9f7; --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #eb6834; --good-text: #006300;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --page: #0d0d0d; --surface-1: #1a1a19; --text-primary: #f0efec; --text-secondary: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --good-text: #0ca30c;
  }
}
* { box-sizing: border-box; }
body { margin: 0; }
body { font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-variant-numeric: tabular-nums; }
.viz-root { background: var(--page); color: var(--text-primary); min-height: 100vh; padding: 16px; }
.wrap { max-width: 1080px; margin: 0 auto; }
h1 { font-size: 20px; margin: 0 0 2px; }
.sub { color: var(--text-secondary); margin: 0 0 16px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; }
.tile, .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
.tile .k { color: var(--text-secondary); font-size: 12px; }
.tile .v { font-size: 24px; font-weight: 600; margin-top: 2px; }
.tile .s { color: var(--muted); font-size: 12px; }
.card { margin-bottom: 16px; }
.card h2 { font-size: 15px; margin: 0 0 4px; }
.note { color: var(--text-secondary); font-size: 12px; margin: 0 0 8px; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
#chart { display: block; width: 100%; height: auto; overflow: visible; }
.legend svg { width: 12px; height: 12px; flex: none; }
.tick { fill: var(--muted); font-size: 11px; }
.ref { fill: var(--text-secondary); font-size: 11px; }
#tip { position: fixed; pointer-events: none; background: var(--surface-1); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 12px; max-width: 280px;
  box-shadow: 0 4px 16px rgba(0,0,0,.15); display: none; z-index: 10; }
#tip b { display: block; margin-bottom: 2px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
.filters button, .filters select { font: inherit; font-size: 13px; padding: 5px 10px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); cursor: pointer; }
.filters button[aria-pressed="true"] { background: var(--text-primary); color: var(--surface-1); }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--text-secondary); font-weight: 500; border-bottom: 1px solid var(--axis);
  padding: 6px 8px; cursor: pointer; white-space: nowrap; user-select: none; }
th.num, td.num { text-align: right; white-space: nowrap; }
td { border-bottom: 1px solid var(--grid); padding: 7px 8px; vertical-align: top; }
td .miss { color: var(--muted); font-size: 12px; }
.tag { display: inline-block; font-size: 11px; border: 1px solid var(--axis); border-radius: 4px; padding: 0 4px;
  margin-left: 4px; color: var(--text-secondary); }
.dot { display: inline-block; width: 10px; height: 10px; vertical-align: -1px; margin-right: 6px; }
.dot.ok { background: var(--series-1); border-radius: 50%; }
.dot.check { background: var(--series-2); transform: rotate(45deg) scale(.85); }
a { color: var(--series-1); }
.foot { color: var(--muted); font-size: 12px; }
</style>
</head>
<body>
<div class="viz-root"><div class="wrap">
  <h1 id="h"></h1>
  <p class="sub" id="sub"></p>
  <div class="tiles" id="tiles"></div>
  <div class="card">
    <h2>Cena a przebieg</h2>
    <p class="note" id="chartnote"></p>
    <div class="legend">
      <span><svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="var(--series-1)"/></svg>Potwierdzone</span>
      <span><svg width="12" height="12" viewBox="0 0 12 12"><path d="M6 0.5 11.5 6 6 11.5 0.5 6Z" fill="var(--series-2)"/></svg>Do sprawdzenia</span>
    </div>
    <svg id="chart" role="img" aria-label="Wykres punktowy: cena ogłoszenia względem przebiegu"></svg>
  </div>
  <div class="card">
    <h2>Wszystkie oferty</h2>
    <div class="filters" id="filters">
      <button data-f="all" aria-pressed="true">Wszystkie</button>
      <button data-f="ok" aria-pressed="false">Potwierdzone</button>
      <button data-f="check" aria-pressed="false">Do sprawdzenia</button>
      <button data-f="new" aria-pressed="false">Nowe i tańsze</button>
    </div>
    <div class="tablewrap"><table id="tbl"><thead><tr>
      <th data-k="model">Model</th><th data-k="price" class="num">Cena</th><th data-k="miles" class="num">Przebieg</th>
      <th data-k="loc">Lokalizacja</th><th data-k="dist" class="num">Odl.</th><th data-k="total" class="num">Koszt całk.</th>
      <th>Link</th></tr></thead><tbody></tbody></table></div>
  </div>
  <p class="foot">Dane z indeksu wyszukiwarki (lub z aimm) – cenę i dostępność potwierdź po kliknięciu.
    Koszt całkowity = cena + koszt przebiegu + szacunkowy dowóz do Des Plaines. Odległość szacunkowa.</p>
</div>
<div id="tip" role="tooltip"></div></div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  const rows = D.rows, M = D.meta;
  const nf = new Intl.NumberFormat("pl-PL");
  const usd = v => v == null ? "–" : nf.format(v) + " USD";
  const mi = v => v == null ? "brak" : nf.format(v) + " mi";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const safeUrl = u => /^https?:\/\//.test(u || "") ? u : null;
  const css = n => getComputedStyle(document.querySelector(".viz-root")).getPropertyValue(n).trim();

  document.getElementById("h").textContent = M.title;
  document.getElementById("sub").textContent = M.date + " · przebieg " + M.run_id +
    " · limit " + usd(M.max_price) + (M.max_miles ? " i " + mi(M.max_miles) : "");

  const ok = rows.filter(r => r.kind === "ok"), chk = rows.filter(r => r.kind === "check");
  const priced = rows.filter(r => r.price != null);
  const best = ok.filter(r => r.total != null).sort((a, b) => a.total - b.total)[0];
  const cheapest = priced.slice().sort((a, b) => a.price - b.price)[0];
  const nNew = rows.filter(r => r.tags.includes("NOWA")).length, nDrop = rows.filter(r => r.tags.includes("TANIEJ")).length;
  const tiles = [
    ["Potwierdzone", ok.length, "spełniają wszystkie kryteria"],
    ["Do sprawdzenia", chk.length, "czegoś brakuje"],
    ["Nowe / tańsze", nNew + " / " + nDrop, "od poprzedniego przebiegu"],
    ["Najlepszy koszt całk.", best ? usd(best.total) : "–", best ? best.loc : "brak potwierdzonych"],
    ["Najniższa cena", cheapest ? usd(cheapest.price) : "–", cheapest ? cheapest.loc : ""],
  ];
  document.getElementById("tiles").innerHTML = tiles.map(t =>
    `<div class="tile"><div class="k">${esc(t[0])}</div><div class="v">${esc(t[1])}</div><div class="s">${esc(t[2])}</div></div>`).join("");

  // ---------- wykres punktowy
  const tip = document.getElementById("tip");
  function showTip(e, r) {
    tip.innerHTML = `<b>${esc(r.model)}</b>${usd(r.price)} · ${mi(r.miles)}<br>${esc(r.loc)}` +
      (r.total != null ? `<br>Koszt całk.: ${usd(r.total)}` : "") +
      (r.missing.length ? `<br>Brakuje: ${esc(r.missing.join("; "))}` : "") +
      (r.change ? `<br>${esc(r.change)}` : "") + `<br><i>kliknij, aby otworzyć ogłoszenie</i>`;
    tip.style.display = "block";
    const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8), y = Math.min(e.clientY + 14, innerHeight - tip.offsetHeight - 8);
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  const hideTip = () => { tip.style.display = "none"; };

  function drawChart() {
    const svg = document.getElementById("chart");
    const W = Math.max(320, svg.parentNode.clientWidth - 28), H = 300, P = {l: 64, r: 16, t: 14, b: 38};
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const pts = rows.filter(r => r.price != null && r.miles != null);
    const noMiles = rows.filter(r => r.price != null && r.miles == null).length;
    const noPrice = rows.filter(r => r.price == null).length;
    document.getElementById("chartnote").textContent = `Każdy punkt to jedna oferta (${pts.length}). ` +
      (noMiles ? `${noMiles} bez przebiegu i ` : "") + (noPrice ? `${noPrice} bez ceny ` : "") +
      ((noMiles || noPrice) ? "są tylko w tabeli. " : "") + "Najlepsze oferty są w lewym dolnym rogu.";
    const xMax = Math.max(M.max_miles || 0, ...pts.map(r => r.miles), 1000);
    const yMin = Math.min(...pts.map(r => r.price), M.max_price) , yLo = Math.max(0, Math.floor((yMin - 500) / 1000) * 1000);
    const yHi = Math.max(M.max_price, ...pts.map(r => r.price));
    const X = v => P.l + v / xMax * (W - P.l - P.r), Y = v => H - P.b - (v - yLo) / (yHi - yLo || 1) * (H - P.t - P.b);
    let g = "";
    const xStep = xMax > 10000 ? 5000 : 2500, yStep = (yHi - yLo) > 6000 ? 2000 : 1000;
    for (let v = 0; v <= xMax; v += xStep)
      g += `<line x1="${X(v)}" x2="${X(v)}" y1="${P.t}" y2="${H - P.b}" stroke="var(--grid)" stroke-width="1"/>` +
           `<text class="tick" x="${X(v)}" y="${H - P.b + 16}" text-anchor="middle">${nf.format(v)}</text>`;
    for (let v = Math.ceil(yLo / yStep) * yStep; v <= yHi; v += yStep)
      g += `<line x1="${P.l}" x2="${W - P.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--grid)" stroke-width="1"/>` +
           `<text class="tick" x="${P.l - 8}" y="${Y(v) + 4}" text-anchor="end">${nf.format(v)}</text>`;
    g += `<line x1="${P.l}" x2="${W - P.r}" y1="${H - P.b}" y2="${H - P.b}" stroke="var(--axis)" stroke-width="1"/>`;
    g += `<text class="tick" x="${(P.l + W - P.r) / 2}" y="${H - 4}" text-anchor="middle">przebieg (mi)</text>`;
    g += `<text class="tick" x="12" y="${(P.t + H - P.b) / 2}" transform="rotate(-90 12 ${(P.t + H - P.b) / 2})" text-anchor="middle">cena (USD)</text>`;
    g += `<line x1="${P.l}" x2="${W - P.r}" y1="${Y(M.max_price)}" y2="${Y(M.max_price)}" stroke="var(--text-secondary)" stroke-dasharray="4 4"/>` +
         `<text class="ref" x="${W - P.r}" y="${Y(M.max_price) - 5}" text-anchor="end">limit ${nf.format(M.max_price)} USD</text>`;
    if (M.max_miles)
      g += `<line x1="${X(M.max_miles)}" x2="${X(M.max_miles)}" y1="${P.t}" y2="${H - P.b}" stroke="var(--text-secondary)" stroke-dasharray="4 4"/>` +
           `<text class="ref" x="${X(M.max_miles) - 5}" y="${H - P.b - 6}" text-anchor="end">limit ${nf.format(M.max_miles)} mi</text>`;
    const ring = css("--surface-1");
    pts.forEach((r, i) => {
      const x = X(r.miles), y = Y(r.price);
      const mark = r.kind === "ok"
        ? `<circle cx="${x}" cy="${y}" r="5.5" fill="var(--series-1)" stroke="${ring}" stroke-width="2"/>`
        : `<path d="M${x} ${y - 7}L${x + 7} ${y}L${x} ${y + 7}L${x - 7} ${y}Z" fill="var(--series-2)" stroke="${ring}" stroke-width="2"/>`;
      g += `<g class="pt" data-i="${rows.indexOf(r)}" style="cursor:pointer">${mark}<circle cx="${x}" cy="${y}" r="12" fill="transparent"/></g>`;
    });
    svg.innerHTML = g;
    svg.querySelectorAll(".pt").forEach(el => {
      const r = rows[+el.dataset.i];
      el.addEventListener("mousemove", e => showTip(e, r));
      el.addEventListener("mouseleave", hideTip);
      el.addEventListener("click", () => { const u = safeUrl(r.url); if (u) window.open(u, "_blank", "noopener"); });
    });
  }

  // ---------- tabela
  let filter = "all", sortK = null, sortDir = 1;
  function drawTable() {
    let list = rows.filter(r => filter === "all" || (filter === "new" ? (r.tags.includes("NOWA") || r.tags.includes("TANIEJ")) : r.kind === filter));
    if (sortK) list = list.slice().sort((a, b) => {
      const va = a[sortK], vb = b[sortK];
      if (va == null) return 1; if (vb == null) return -1;
      return (typeof va === "number" ? va - vb : String(va).localeCompare(String(vb), "pl")) * sortDir;
    });
    document.querySelector("#tbl tbody").innerHTML = list.map(r => {
      const u = safeUrl(r.url);
      const tags = r.tags.map(t => `<span class="tag">${esc(t)}</span>`).join("") + (r.title && r.title !== "clean" ? `<span class="tag">${esc(r.title)}</span>` : "");
      const miss = r.missing.length ? `<div class="miss">Brakuje: ${esc(r.missing.join("; "))}</div>` : "";
      const ch = r.change ? `<div class="miss">${esc(r.change)}</div>` : "";
      const link = u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${r.direct ? "ogłoszenie" : "strona z ofertą"}</a>` : "brak";
      return `<tr><td><span class="dot ${r.kind}"></span>${esc(r.model)}${tags}${miss}${ch}</td>` +
        `<td class="num">${usd(r.price)}</td><td class="num">${mi(r.miles)}</td><td>${esc(r.loc)}</td>` +
        `<td class="num">${r.dist == null ? "–" : nf.format(r.dist) + " mi"}</td><td class="num">${usd(r.total)}</td><td>${link}</td></tr>`;
    }).join("") || `<tr><td colspan="7">Brak ofert w tym widoku.</td></tr>`;
  }
  document.getElementById("filters").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    filter = b.dataset.f;
    document.querySelectorAll("#filters button").forEach(x => x.setAttribute("aria-pressed", x === b));
    drawTable();
  });
  document.querySelectorAll("#tbl th[data-k]").forEach(th => th.addEventListener("click", () => {
    sortDir = sortK === th.dataset.k ? -sortDir : 1; sortK = th.dataset.k; drawTable();
  }));
  drawChart(); drawTable();
  addEventListener("resize", drawChart);
})();
</script>
</body>
</html>
"""
