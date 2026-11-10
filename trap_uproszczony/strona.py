# -*- coding: utf-8 -*-
"""
Strona „Trap aluminiowy V2 – model 3D” (jeden plik HTML: model glTF w środku, three.js z CDN).
  python3 strona.py   ->  trap_v2_strona.html
Dane: generuj.py (obliczenia, części, śruby, podnoszenie), podglad3d.py (model 3D, otwory), lista_zakupow.csv.
"""
import base64, csv, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g
import podglad3d as p3
import stal

OUT = os.path.dirname(os.path.abspath(__file__))
E = html.escape


def pill(u, info=False):
    cls = "info" if info else ("ok" if u < 0.8 else ("warn" if u <= 1.0 else "bad"))
    return f'<span class="pill {cls}">{u * 100:.0f}%</span>'


def chart(lift, lift0):
    W, H, x0, x1, y0, y1 = 640, 230, 44, 630, 200, 22
    dmin, dmax, kmax = -15, 95, 40
    X = lambda d: x0 + (d - dmin) / (dmax - dmin) * (x1 - x0)
    Y = lambda k: y0 - k / kmax * (y0 - y1)
    s = [f'<svg viewBox="0 0 {W} {H + 20}" width="100%" role="img" aria-label="Siła przy podnoszeniu trapu">']
    for k in range(0, kmax + 1, 10):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(k):.1f}" y2="{Y(k):.1f}" stroke="var(--line)"/>'
                 f'<text x="{x0 - 6}" y="{Y(k) + 4:.1f}" text-anchor="end" font-size="11" fill="var(--mut)">{k}</text>')
    for d in (-10, 0, 15, 30, 45, 60, 75, 90):
        s.append(f'<text x="{X(d):.1f}" y="{H - 8}" text-anchor="middle" font-size="11" fill="var(--mut)">{d}°</text>')
    for rows, col, dash, w in ((lift0, "var(--mut)", ' stroke-dasharray="5 4"', 2), (lift, "var(--acc)", "", 2.5)):
        pts = " ".join(f"{'M' if i == 0 else 'L'}{X(r['deg']):.1f},{Y(max(r['user_kg'], 0)):.1f}" for i, r in enumerate(rows))
        s.append(f'<path d="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{dash}/>')
    m0, m1 = max(lift0, key=lambda r: r["user_kg"]), max(lift, key=lambda r: r["user_kg"])
    for r, col, lab, dy in ((m0, "var(--mut)", "bez sprężyn", -8), (m1, "var(--acc)", "ze sprężynami", 20)):
        s.append(f'<circle cx="{X(r["deg"]):.1f}" cy="{Y(r["user_kg"]):.1f}" r="4" fill="{col}"/>'
                 f'<text x="{X(r["deg"]) + 10:.1f}" y="{Y(r["user_kg"]) + dy:.1f}" font-size="12" fill="{col}">'
                 f'{lab}: max {r["user_kg"]:.0f} kg</text>')
    s.append(f'<text x="{x1}" y="{y1 - 2}" text-anchor="end" font-size="11" fill="var(--mut)">kg na końcu sekcji A</text></svg>')
    return "".join(s)


def table(head, rows, num=()):
    th = "".join(f'<th{" class=num" if i in num else ""}>{h}</th>' for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td{" class=num" if i in num else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def main():
    (mA, cAs, cAz), (mB, cBs, cBz) = g.masses()
    rows = g.calcs(mA, mB)
    lift = g.lift_table(mA, cAs, cAz, mB, cBs, cBz, True)
    lift0 = g.lift_table(mA, cAs, cAz, mB, cBs, cBz, False)
    bom = g.build_bom()
    bolts, sleeves = g.build_bolts()
    with open(os.path.join(OUT, "lista_zakupow.csv"), encoding="utf-8-sig") as f:
        buy = list(csv.reader(f, delimiter=";"))[1:]
    M = p3.build()
    glb_path = os.path.join(OUT, "www", "trap_v2.glb")
    p3.write_gltf(glb_path, M=M)
    glb = base64.b64encode(open(glb_path, "rb").read()).decode()
    real = [r for r in rows if not r["nazwa"].startswith("[INFO]")]
    worst = max(real, key=lambda r: r["wytezenie"])
    kinds = dict(M.bolt_axes)
    n_holes, n_join = len(M.hole_dia), len(M.bolt_axes)

    calc_rows = [[f'{E(r["nazwa"].replace("[INFO] ", ""))}<span class="note">{E(r["uwagi"])}</span>',
                  f'{r["obciazenie"]:g} / {r["nosnosc"]:g} {E(r["jedn"])}', pill(r["wytezenie"], r["nazwa"].startswith("[INFO]"))]
                 for r in rows]
    bom_rows = [[f'<b>{E(b["pid"])}</b> {E(b["name"])}<span class="note">{E(b["how"])} · {E(b["where"])}</span>',
                 b["qty"], E(b["size"]), f'{b["mass"]:g}'] for b in bom]
    bolt_rows = [[E(b[0]), E(b[1]) + f'<span class="note">{E(b[3])}</span>', b[2]] for b in bolts] + \
                [[f"tuleja {E(t)} × {L:g}", f'stal, rura bezszwowa ocynk<span class="note">{E(why)}</span>', q] for (t, L, q, why) in sleeves]
    hole_rows = [[i, f"Ø{p3.fmt(M.hole_dia[k])}", E(kinds.get(k, "–")), "<br>".join(E(t) for t in M.hole_txt[k])]
                 for i, k in enumerate(sorted(M.hole_dia, key=lambda k: (M.hole_txt[k][0])), 1)]
    buy_rows = [[E(a), E(b), E(c)] for a, b, c in buy if a]

    steps = [
        ("Zmierz przyczepę", ["Wysokość podłogi nad ziemią (policzone na 480 mm), przekrój tylnej belki (w modelu 50×75×3) i szerokość między burtami.",
                              "Podeślij te wymiary – dopasuję wsporniki K, śruby do belki i kąt, zanim zaczniesz wiercić."]),
        ("Kup materiał", ["Według tabeli „Zakupy” niżej. Rury jezdne MUSZĄ być z EN AW-6082-T6 (PA4) – z 6060 trap nie przechodzi obliczeń."]),
        ("Przetnij profile", ["Rury 1250 mm, poprzeczki 1190 mm, prowadnice 1095 i 715 mm.",
                              f"W 8 podłużnicach sekcji B skos przy ziemi {g.SKOS:.0f} mm: dno utnij na {g.L_SEC - g.SKOS:.0f} mm, boki ukośnie do górnej krawędzi na końcu."]),
        ("Płyty stalowe", ["Same prostokąty z płaskownika – tylko proste cięcia. Płyty H (4 szt.) i Z (8 szt.) wierć w pakiecie, wtedy są identyczne.",
                           "Szablony 1:1 (szablony_1do1_v2.pdf) – drukuj 100 %, sprawdź kwadrat 50 mm."]),
        ("Otwory w rurach", ["Wg kart w rysunki_trap_v2.pdf i tabeli „Otwory” niżej. Pionowe otwory przez rurę i poprzeczkę wierć wiertarką stołową lub z prowadnikiem.",
                             "Otwór pod tuleję = Ø tulei + 0,5 mm (Ø12,5 / Ø18,5). Tuleja ma długość profilu – nie zgniata aluminium."]),
        ("Zawias środkowy", ["L1 i L3 czołami na równej podłodze, górne krawędzie stykają się. Przyłóż płyty Z, włóż sworzeń M20, dopiero wtedy wierć rury przez płyty.",
                             "Płyty sekcji B na zewnątrz płyt A, na podkładkach 6 mm."]),
        ("Ruszt i siatka", ["Do góry nogami: podłużnice, poprzeczki, tuleje Ø12×1,5 dł. 159,5, śruby M8×200 (20 N·m).",
                            "Odwróć, siatka (LWD w poprzek) na wkręty 4,8×19 co ~250 mm, prowadnice na siatce śrubami M8×130."]),
        ("Na przyczepie", ["Wsporniki K do belki (M12×80 + tuleje w belce). Sworznie M20 nie dokręcaj na sztywno – mają się obracać.",
                           "Sprężyny 460/200 mm 1600 N: dolne oczko na K, górne na płycie S. Stal ↔ aluminium: pasta cynkowa i podkładki izolujące."]),
        ("Przed pierwszym użyciem", ["Próba 400 kg przy zawiasie środkowym (nad rurą wewnętrzną, nad zewnętrzną, 50 mm od podłogi) – nic nie może zostać wygięte.",
                                     "Pierwszy wjazd bez kierowcy, przyczepa podpięta do auta. Po 3–5 wjazdach dokręć śruby."]),
        ("Do jazdy i z powrotem", ["Podnoś sekcję A za zawias środkowy – B wlecze się, potem zawisa pod A. W pionie: 2 sworznie Ø12 przez K i H, zapięcia.",
                                   "Rozkładasz odwrotnie. Nie trzymaj palców między sekcjami przy zawiasie."]),
    ]
    steps_html = "".join(f"<li><b>{E(t)}</b><ul>" + "".join(f"<li>{E(x)}</li>" for x in xs) + "</ul></li>" for t, xs in steps)
    cmp_rows = [["profile aluminiowe", "7", "5"], ["rodzaje części / sztuk (bez śrub)", "26 / 79", f"{len(bom)} / {sum(b['qty'] for b in bom)}"],
                ["otwory", "376", f"{n_holes} miejsc ({sum(b['holes'] * b['qty'] for b in bom)} w częściach)"],
                ["rodzaje tulei / sztuk", "9 / 169", f"{len(sleeves)} / {sum(s[2] for s in sleeves)}"],
                ["płyty stalowe", "7 kształtów, wielokąty", "4, same prostokąty"],
                ["masa trapu", "72,4 kg", f"{mA + mB:.0f} kg"],
                ["podnoszenie ze sprężynami / bez", "24,6 / 40,1 kg", f"{max(r['user_kg'] for r in lift):.1f} / {max(r['user_kg'] for r in lift0):.1f} kg"]]

    kv = [(f"2,5 × {g.WIDTH / 1000:.2f} m".replace(".", ","), "trap rozłożony, 2 sekcje po 1,25 m"),
          (f"{g.ALPHA:.1f}°".replace(".", ","), f"kąt przy podłodze {g.H_FLOOR / 10:.0f} cm"),
          (f"~{mA + mB:.0f} kg", f"trap (+ wsporniki K {4 * 1.9e3 * 130 * g.RHO_ST:.1f} kg)".replace(".", ",")),
          (f"~{max(r['user_kg'] for r in lift0):.0f} kg", f"podnoszenie bez sprężyn; ze sprężynami {max(r['user_kg'] for r in lift):.0f} kg"),
          (f"{(g.H_FLOOR + 25 + g.L_SEC) / 1000:.2f} m".replace(".", ","), "góra trapu do jazdy"),
          (f"{worst['wytezenie'] * 100:.0f}%", "najbardziej obciążona część"),
          (f"{n_holes} / {n_join}", "otwory / złącza w modelu, 0 kolizji")]
    kv_html = "".join(f"<div><b>{E(a)}</b><span>{E(b)}</span></div>" for a, b in kv)

    st = stal.main()
    sd = json.load(open(os.path.join(OUT, "stal_dane.json"), encoding="utf-8"))
    sp = st["sprezyny_stal"]
    al_l0, al_l = max(r["user_kg"] for r in lift0), max(r["user_kg"] for r in lift)
    vs_rows = [["masa trapu", f"{mA + mB:.0f} kg", f"{st['masa_stal']:.0f} kg"],
               ["siła przy podnoszeniu bez sprężyn", f"{al_l0:.0f} kg", f"{st['wysilek_bez_sprezyn_stal']:.0f} kg"],
               ["sprężyny gazowe", "2 × 1600 N (Ø28)", f"{sp['sztuk']} × {sp['F1_N']} N" + (" (Ø40, oś M16)" if sp["F1_N"] > 2500 else " (Ø28)")],
               ["siła przy podnoszeniu ze sprężynami", f"{al_l:.0f} kg", f"{sp['max_wysilek_kg']:.0f} kg"],
               ["korozja", "nie rdzewieje, bez malowania", "cynkowanie ogniowe po wierceniu albo farba"],
               ["koszt materiału (orientacyjnie, netto)", f"{st['koszt_al']} zł", f"{st['koszt_stal']} zł z cynkiem · "
                f"{st['koszt_stal'] - sd['koszty'][5][3] + stal.CENY['farba_kpl']:.0f} zł z farbą"],
               ["rysunki, szablony, otwory, model 3D", "–", "bez zmian (inne tylko grubości ścianek)"],
               ["najbardziej obciążona część", f"{worst['wytezenie'] * 100:.0f}%", f"{st['najwieksze_wytezenie']['wartosc'] * 100:.0f}%"]]
    cost_rows = [[E(r[0]) + (f'<span class="note">S2: {E(r[4])}</span>' if r[4] else ""), f"{r[1]} zł", f"{r[2]} zł", f"<b>{r[3]} zł</b>"]
                 for r in sd["koszty"]]
    var_rows = [[f"<b>{E(x['klucz'])}</b> {E(x['nazwa'])}" + (" <span class='pill ok'>polecana stalowa</span>" if x["klucz"] == sd["podsumowanie"]["polecany"] else "")
                 + f"<span class='note'>rysunki: {E(x['rysunki'])}</span>",
                 f"{x['masa']:.0f} kg", f"{x['bez']:.0f} kg", f"{x['ze']:.0f} kg<span class='note'>{E(x['sprezyny'])}</span>", f"{x['koszt']} zł",
                 pill(x["wyt"])] for x in sd["warianty"]]
    st_calc = [[f'{E(r["nazwa"])}<span class="note">{E(r["uwagi"])}</span>', f'{r["obciazenie"]:g} / {r["nosnosc"]:g} {E(r["jedn"])}',
                pill(r["wytezenie"])] for r in sd["obliczenia"]]
    st_buy = [[E(a), E(b), E(c)] for a, b, c in sd["zakupy"]]
    ceny = ", ".join(f"{E(k)} {v:g}" for k, v in stal.CENY.items())
    page = TEMPLATE
    for k, v in {"%KV%": kv_html, "%CHART%": chart(lift, lift0), "%CALC%": table(["Sprawdzenie", "Obciążenie / nośność", "Wytężenie"], calc_rows, (1, 2)),
                 "%CMP%": table(["", "poprzednio", "teraz (V2)"], cmp_rows, (1, 2)), "%STEPS%": steps_html,
                 "%BOM%": table(["Część", "Szt.", "Wymiar [mm]", "kg/szt."], bom_rows, (1, 2, 3)),
                 "%BOLTS%": table(["Rozmiar", "Rodzaj / gdzie", "Szt."], bolt_rows, (2,)),
                 "%HOLES%": table(["Nr", "Ø", "Złącze", "Miejsce wiercenia w każdej części, przez którą przechodzi"], hole_rows, (0, 1)),
                 "%BUY%": table(["Pozycja", "Ilość", "Uwagi"], buy_rows), "%NHOLES%": str(n_holes),
                 "%VS%": table(["", "aluminium (V2)", "stal lekka (S2)"], vs_rows, (1, 2)),
                 "%STCOST%": table(["Pozycja", "aluminium", "stal ciężka S1", "stal lekka S2"], cost_rows, (1, 2, 3)),
                 "%STVAR%": table(["Wariant", "Masa", "Podnoszenie bez sprężyn", "Ze sprężynami", "Koszt (z cynkiem)", "Wytężenie max"], var_rows, (1, 2, 3, 4, 5)),
                 "%STCALC%": table(["Sprawdzenie", "Obciążenie / nośność", "Wytężenie"], st_calc, (1, 2)),
                 "%STBUY%": table(["Pozycja", "Ilość", "Uwagi"], st_buy), "%CENY%": ceny,
                 "%MST%": f"{st['masa_stal']:.0f}", "%MAL%": f"{mA + mB:.0f}",
                 "%WORST%": E(worst["nazwa"]), "%GLB%": glb}.items():
        page = page.replace(k, v)
    with open(os.path.join(OUT, "trap_v2_strona.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("trap_v2_strona.html", f"{len(page) / 1e6:.1f} MB")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trap aluminiowy V2 – model 3D</title>
<style>
/* jeden słupek treści 1000 px: model 3D na górze, liczby, potem obliczenia i dane warsztatowe */
:root { --bg:#f5f6f7; --card:#fff; --ink:#1d2228; --mut:#5f6b76; --line:#e2e6ea; --acc:#2f6fb3; --ok:#2f8a4f; --warn:#c07a12; --bad:#c0392b; --viewer:#e9ecef;
        --body:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; color-scheme:light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#14171a; --card:#1c2024; --ink:#e7eaed; --mut:#9aa5b0; --line:#2c3238; --acc:#6aa5e6; --viewer:#22272c; color-scheme:dark; } }
:root[data-theme="dark"] { --bg:#14171a; --card:#1c2024; --ink:#e7eaed; --mut:#9aa5b0; --line:#2c3238; --acc:#6aa5e6; --viewer:#22272c; color-scheme:dark; }
* { box-sizing:border-box; } body { margin:0; font:15px/1.5 var(--body); background:var(--bg); color:var(--ink); }
main { max-width:1000px; margin:0 auto; padding:20px 16px 60px; } h1 { font-size:26px; margin:6px 0 4px; text-wrap:balance; } h2 { font-size:18px; margin:28px 0 10px; text-wrap:balance; }
.lede { color:var(--mut); margin:0 0 14px; max-width:72ch; } .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; }
#stage { position:relative; height:clamp(340px,62vh,600px); background:var(--viewer); border-radius:12px; overflow:hidden; touch-action:none; }
#stage canvas { display:block; }
.bar { display:flex; gap:8px; margin:10px 0; flex-wrap:wrap; align-items:center; }
button { border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:999px; padding:7px 14px; font:inherit; font-size:14px; cursor:pointer; }
button:hover { border-color:var(--acc); } button:focus-visible, input:focus-visible { outline:2px solid var(--acc); outline-offset:2px; }
button[aria-pressed=true] { background:var(--acc); color:#fff; border-color:var(--acc); }
.bar label { color:var(--mut); font-size:13px; } #pos { flex:1; min-width:160px; accent-color:var(--acc); }
.kv { display:grid; grid-template-columns:repeat(auto-fit,minmax(128px,1fr)); gap:10px; } .kv div { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 12px; }
.kv b { display:block; font-size:20px; font-variant-numeric:tabular-nums; } .kv span { color:var(--mut); font-size:13px; }
.tw { overflow-x:auto; } table { width:100%; border-collapse:collapse; } td,th { padding:8px 6px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { color:var(--mut); font-weight:500; font-size:13px; } .num { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; } .note { display:block; color:var(--mut); font-size:12.5px; }
.pill { padding:2px 8px; border-radius:999px; font-weight:600; font-size:13px; } .ok { background:#2f8a4f22; color:var(--ok); } .warn { background:#c07a1222; color:var(--warn); }
.bad { background:#c0392b22; color:var(--bad); } .info { background:var(--line); color:var(--mut); }
ol li { margin-bottom:8px; } ul { margin:4px 0; padding-left:18px; }
.hint { position:absolute; left:12px; bottom:10px; font-size:12.5px; color:var(--mut); pointer-events:none; }
#info { position:absolute; right:10px; top:10px; width:min(380px, calc(100% - 20px)); max-height:calc(100% - 20px); overflow:auto; background:var(--card);
        border:1px solid var(--line); border-radius:10px; padding:10px 12px; font-size:13px; white-space:pre-line; display:none; box-shadow:0 2px 10px #0002; }
#info b { display:block; margin-bottom:4px; white-space:normal; } #info .x { float:right; border:0; padding:0 4px; background:none; color:var(--mut); }
#tip { position:absolute; pointer-events:none; background:var(--ink); color:var(--bg); font-size:12px; padding:3px 7px; border-radius:6px; display:none; max-width:320px; }
.legend { display:flex; flex-wrap:wrap; gap:6px 14px; font-size:13px; color:var(--mut); margin:4px 0 0; }
.legend i { display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:5px; vertical-align:-1px; }
#holes td:last-child { font-size:13px; }
</style></head><body><main>
<h1>Trap aluminiowy 2,5 × 1,19 m – wersja bez spawania (V2)</h1>
<p class="lede">Wszystko skręcane: 4 rury pod koło 100×40×3 z 6082-T6 (pas 282 mm między prowadnicami), podłużnice i poprzeczki z rur aluminiowych, siatka na całym pokładzie, płyty stalowe tylko prostokątne. Model pokazuje każdy otwór, śrubę, tuleję i sworzeń w miejscu z tabel otworów. Kliknij element, otwór albo śrubę, żeby zobaczyć wymiary.</p>
<div id="stage"><div class="hint" id="hint">Wczytuję model…</div><div id="tip"></div>
  <div id="info" role="dialog" aria-live="polite"><button class="x" id="ix" aria-label="Zamknij opis">✕</button><b id="it"></b><span id="ib"></span></div></div>
<div class="bar">
  <button id="b-roz" aria-pressed="true">Rozłożony</button><button id="b-anim" aria-pressed="false">▶ Składanie</button><button id="b-tr" aria-pressed="false">Do jazdy</button>
  <label for="pos">pozycja</label><input id="pos" type="range" min="0" max="1" step="0.002" value="0">
</div>
<div class="bar">
  <button data-f="A:pinTr:1">Zawias przy przyczepie</button><button data-f="A:pinMid:1">Zawias środkowy</button><button data-f="A:M8x:340:+125">Skrzyżowanie</button>
  <button data-f="A:M12oko:1">Sprężyna</button><button data-f="B:T">Listwa T</button><button id="b-all">Cały trap</button>
</div>
<div class="bar">
  <button class="lay" data-k="śruba" aria-pressed="true">Śruby</button><button class="lay" data-k="tuleja" aria-pressed="true">Tuleje</button>
  <button class="lay" data-k="siatka" aria-pressed="true">Siatka</button><button class="lay" data-k="przyczepa" aria-pressed="true">Przyczepa</button>
  <button id="b-x" aria-pressed="false">Profile przezroczyste</button><button id="b-drill" aria-pressed="false">Tylko otwory</button>
</div>
<div class="legend"><span><i style="background:#8fa9c9"></i>rury jezdne 6082-T6</span><span><i style="background:#c9cfd6"></i>podłużnice 100×40×2</span>
<span><i style="background:#d8b98a"></i>poprzeczki 60×40×3</span><span><i style="background:#3f6fb0"></i>prowadnice</span><span><i style="background:#3a3a3a"></i>płyty H / Z / S</span>
<span><i style="background:#b04a3a"></i>wsporniki K</span><span><i style="background:#e01b1b"></i>otwory</span><span><i style="background:#a9afb6"></i>śruby</span><span><i style="background:#d4b030"></i>tuleje</span></div>
<h2>Do czego są prowadnice i listwa T</h2>
<div class="card"><p style="margin:0 0 8px"><b>Prowadnice koła</b> to dwa niebieskie kątowniki 40×40×4 leżące na siatce, wzdłuż całego trapu. Ich pionowe ścianki
(35 mm nad siatką, 282 mm od siebie) trzymają koło na 4 rurach jezdnych. Koło waży z kierowcą do 273 kg i może jechać tylko po tych rurach. Bez prowadnic koło przy
pchaniu motocykla łatwo zjedzie na siatkę obok, a tam siatka leży na przęsłach do 190 mm i jest liczona tylko na stopę człowieka – mogłaby się zarwać.</p>
<p style="margin:0"><b>Listwa T</b> to płaskownik 40×5 przynitowany od spodu do końca sekcji B, 650 mm od zawiasu. Koniec B leży na ziemi i nie ma tam poprzeczki
(byłaby za nisko, ocierałaby o ziemię), więc listwa trzyma 8 podłużnic w równym rozstawie. Bez niej końce rur rozjeżdżałyby się na boki.</p></div>
<h2>W liczbach</h2>
<div class="kv">%KV%</div>
<h2>Siła przy podnoszeniu i opuszczaniu</h2><div class="card">%CHART%
<p class="note">Siła prostopadle do trapu na końcu sekcji A (przy zawiasie środkowym). Ujemny kąt = trap leży na ziemi, 90° = pion. Skok przy ~45°: sekcja B przestaje wlec się po ziemi i zawisa w całości na zawiasie. W pionie trap jest prawie w równowadze – nie spada sam.</p></div>
<h2>Obliczenia (motocykl 350 kg + kierowca 105 kg)</h2>
<div class="card">%CALC%
<p class="note">Koło 273 kg (60 % z 455 kg) ×1,5 (dynamika) ×1,5; stopa 105 kg ×1,5 ×1,5; ciężar własny ×1,35. Najbardziej wytężone: %WORST%. Wiersz szary pokazuje, czemu rury jezdne muszą być z 6082-T6. Ręczne obliczenia w stylu EN 1999 / EN 1993, nie MES. Nie liczę belki Twojej przyczepy ani siatki – dostawca siatki powinien potwierdzić 160 kg w punkcie na przęśle 190 mm.</p></div>
<h2>Co jest prostsze niż w poprzedniej wersji</h2><div class="card">%CMP%</div>
<h2>Montaż i użytkowanie</h2><div class="card"><ol>%STEPS%</ol></div>
<h2>Części</h2><div class="card">%BOM%</div>
<h2>Śruby, sworznie, tuleje</h2><div class="card">%BOLTS%
<p class="note">8.8 ocynk z podkładkami, nakrętki samohamowne. M8 20 N·m, M12 40 N·m (na tulejach). Sworzni M20 nie dokręcaj na sztywno.</p></div>
<h2>Otwory – miejsca wiercenia (%NHOLES%)</h2><div class="card" id="holes">%HOLES%
<p class="note">s – od końca sekcji (A: przy przyczepie, B: przy zawiasie środkowym), x – od osi trapu, z – od spodu rury. Otwór przechodzący przez kilka części wierć razem albo przez płytę jako szablon. Model sprawdza, że każda śruba przechodzi przez otwory we wszystkich częściach, bez kolizji z materiałem.</p></div>
<h2>Zakupy</h2><div class="card">%BUY%</div>
<h2>Wariant stalowy – lekki (S2)</h2>
<div class="card"><p style="margin:0 0 10px">Ten sam trap: identyczny układ, wymiary zewnętrzne profili, otwory, rysunki, szablony i model 3D. Zmieniają się tylko materiał i grubości:
rury jezdne 100×40×<b>2</b> ze stali <b>S355</b> (mocniejszej, więc może być cieńsza), podłużnice chodnika 100×40×<b>1,5</b>, poprzeczki 60×40×2, lżejsza siatka stalowa ocynkowana
i mocniejsze sprężyny. Trap waży %MST% kg zamiast %MAL% kg (pierwsza wersja stalowa z grubymi ściankami miała 150 kg).</p>
%VS%
<p class="note">Rury jezdne muszą być ze stali S355 (S355J2H lub S355MH) – z S235 przy ściance 2 mm są za słabe. Jeśli hurtownia nie ma S355, weź 100×40×3 S235 (+20 kg, jak w wariancie S1).
Oś oczek sprężyn: śruba M16 z tuleją Ø25×5, otwór oczka w K i S rozwierć z Ø13 do Ø17. Sworznie blokady ze stali 8.8. Wszystkie części stalowe cynkuj ogniowo PO wierceniu albo pomaluj.</p></div>
<h3 style="font-size:15px;margin:16px 0 8px">Porównanie wariantów</h3><div class="card">%STVAR%
<p class="note">Lżej niż S2 w stali da się zejść tylko zmniejszając trap: S3 ma chodnik tylko z lewej strony (motocykl pchasz z lewej, od strony stopki) i szerokość 740 mm – wymaga nowych rysunków.
Sprężyny dobrane tak, żeby rozłożony trap zawsze leżał na ziemi, a w pionie nie pchał do przyczepy.</p></div>
<h3 style="font-size:15px;margin:16px 0 8px">Porównanie kosztów materiału</h3><div class="card">%STCOST%
<p class="note">Ceny to założenia (netto, PLN) – sprawdź w swojej hurtowni i wpisz w stal.py (CENY): %CENY%. Profile liczone w całych sztangach 6 m.</p></div>
<h3 style="font-size:15px;margin:16px 0 8px">Obliczenia wariantu stalowego lekkiego (S2)</h3><div class="card">%STCALC%</div>
<h3 style="font-size:15px;margin:16px 0 8px">Zakupy – wariant stalowy lekki (S2)</h3><div class="card">%STBUY%</div>
<h2>Pliki</h2><div class="card"><p>Rysunki z tabelami otworów, szablony 1:1, DXF, listy CSV, model glTF i skrypty (generuj.py, podglad3d.py, strona.py) są w katalogu trap_uproszczony w repozytorium.</p></div>
</main>
<script type="application/octet-stream" id="glb">%GLB%</script>
<script type="importmap">{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const $ = id => document.getElementById(id);
const stage = $('stage');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.localClippingEnabled = true; stage.prepend(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.005, 60);
const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.05));
const dl = new THREE.DirectionalLight(0xffffff, 1.0); dl.position.set(3, 4, -2); scene.add(dl);
const dl2 = new THREE.DirectionalLight(0xffffff, 0.45); dl2.position.set(-2, -1, 2); scene.add(dl2);
const grid = new THREE.GridHelper(8, 32, 0x999999, 0xbbbbbb); grid.material.opacity = 0.35; grid.material.transparent = true; grid.position.y = -0.48; scene.add(grid);
function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
const VIEW = [[3.4, 1.8, -4.2], [0, -0.15, -1.1]];
function view(pos, tgt) { camera.position.set(...pos); controls.target.set(...tgt); controls.update(); }
view(...VIEW);

let model, mixer, action, dur = 1, t = 0, anim = 0;
const pos = $('pos');
function setPos(v) {
  t = Math.min(1, Math.max(0, v)); pos.value = t;
  if (mixer) { action.time = t * dur * 0.9999; mixer.update(0); }
  $('b-roz').setAttribute('aria-pressed', t === 0); $('b-tr').setAttribute('aria-pressed', t === 1);
}
const bin = Uint8Array.from(atob($('glb').textContent.trim()), c => c.charCodeAt(0)).buffer;
new GLTFLoader().parse(bin, '', gl => {
  model = gl.scene; scene.add(model);
  model.traverse(o => { if (!o.isMesh) return; o.material = o.material.clone(); o.userData.op = o.material.opacity; o.userData.tr = o.material.transparent;
                        if (o.material.transparent) o.material.depthWrite = false; });
  mixer = new THREE.AnimationMixer(model);
  const c = gl.animations.find(a => a.name === 'skladanie') || gl.animations[0]; dur = c.duration;
  action = mixer.clipAction(c); action.play(); action.paused = true;
  setPos(0); layers();
  $('hint').textContent = 'Przeciągnij, aby obrócić · kółko / szczypnięcie przybliża · kliknij element, otwór albo śrubę';
}, err => { $('hint').textContent = 'Nie udało się wczytać modelu.'; console.error(err); });

// warstwy
const hidden = new Set(); let drill = false, xray = false;
function layers() {
  if (!model) return;
  model.traverse(o => {
    if (!o.isMesh) return;
    const k = o.userData.rodzaj;
    if (['śruba', 'tuleja', 'siatka', 'przyczepa', 'sprężyna'].includes(k))
      o.visible = !hidden.has(k) && !(drill && ['śruba', 'tuleja', 'siatka', 'sprężyna'].includes(k));
    if (k === 'profil' || k === 'płyta') {
      o.material.transparent = xray || o.userData.tr; o.material.opacity = xray ? 0.28 : o.userData.op; o.material.depthWrite = !xray;
    }
  });
  $('b-drill').setAttribute('aria-pressed', drill); $('b-x').setAttribute('aria-pressed', xray);
}
document.querySelectorAll('.lay').forEach(b => b.onclick = () => {
  const k = b.dataset.k; hidden.has(k) ? hidden.delete(k) : hidden.add(k); b.setAttribute('aria-pressed', !hidden.has(k)); layers(); });
$('b-drill').onclick = () => { drill = !drill; layers(); };
$('b-x').onclick = () => { xray = !xray; layers(); };

// ruch
pos.oninput = () => { anim = 0; setPos(+pos.value); };
$('b-roz').onclick = () => { anim = 0; setPos(0); };
$('b-tr').onclick = () => { anim = 0; setPos(1); };
$('b-anim').onclick = () => { anim = t > 0.5 ? -1 : 1; };
$('b-all').onclick = () => view(...VIEW);

// przybliżenia i opisy
document.querySelectorAll('[data-f]').forEach(b => b.onclick = () => {
  let obj = null; model && model.traverse(o => { if (o.userData.id === b.dataset.f) obj = o; });
  if (!obj) return;
  const box = new THREE.Box3().setFromObject(obj), c = box.getCenter(new THREE.Vector3());
  const r = Math.max(0.5, Math.min(1.6, box.getSize(new THREE.Vector3()).length() * 1.6));
  const dir = camera.position.clone().sub(controls.target).normalize();
  view(c.clone().addScaledVector(dir, r).toArray(), c.toArray()); select(obj);
});
const ray = new THREE.Raycaster(), tip = $('tip');
const visible = o => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
function pick(e) {
  if (!model) return null;
  const r = renderer.domElement.getBoundingClientRect();
  ray.setFromCamera({ x: (e.clientX - r.left) / r.width * 2 - 1, y: -(e.clientY - r.top) / r.height * 2 + 1 }, camera);
  const h = ray.intersectObject(model, true).find(h => visible(h.object) && h.object.userData.rodzaj !== 'siatka');
  return h ? h.object : null;
}
let sel = null;
function select(o) {
  if (sel && sel.material.emissive) sel.material.emissive.setHex(0);
  sel = o;
  if (!o) { $('info').style.display = 'none'; return; }
  if (o.material.emissive) o.material.emissive.setHex(0x553300);
  const L = (o.userData.nazwa || '').split('\n'); $('it').textContent = L[0]; $('ib').textContent = L.slice(1).join('\n');
  $('info').style.display = 'block';
}
$('ix').onclick = () => select(null);
renderer.domElement.addEventListener('pointermove', e => {
  if (e.buttons) return; const o = pick(e), r = stage.getBoundingClientRect();
  if (o && o.userData.nazwa) { tip.style.display = 'block'; tip.textContent = o.userData.nazwa.split('\n')[0];
    tip.style.left = (e.clientX - r.left + 12) + 'px'; tip.style.top = (e.clientY - r.top + 12) + 'px'; } else tip.style.display = 'none';
});
renderer.domElement.addEventListener('pointerleave', () => tip.style.display = 'none');
let down = null;
renderer.domElement.addEventListener('pointerdown', e => down = [e.clientX, e.clientY]);
renderer.domElement.addEventListener('pointerup', e => { if (down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) < 5) select(pick(e)); });

const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (anim) { if (reduce) { setPos(anim > 0 ? 1 : 0); anim = 0; } else { const v = t + anim * dt / 6; if (v >= 1 || v <= 0) anim = 0; setPos(v); } }
  $('b-anim').setAttribute('aria-pressed', anim !== 0);
  controls.update(); renderer.render(scene, camera);
});
</script></body></html>
"""

if __name__ == "__main__":
    main()
