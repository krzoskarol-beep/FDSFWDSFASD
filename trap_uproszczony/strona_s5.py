# -*- coding: utf-8 -*-
"""
Strona „Trap stalowy S5 – model 3D” (jeden plik HTML, model glTF w środku, three.js z CDN).
  python3 strona_s5.py   ->  stal_S5/trap_s5_strona.html
"""
import base64, csv, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g
import podglad3d as p3
import stal
import stal_s5 as s5
from strona import TEMPLATE, chart, pill, table

E = html.escape
HEAD = TEMPLATE[:TEMPLATE.index("<h1>")].replace("Trap aluminiowy V2 – model 3D", "Trap stalowy S5 – model 3D")
TAIL = TEMPLATE[TEMPLATE.index('<script type="application/octet-stream"'):].replace("const VIEW = [[3.4, 1.8, -4.2], [0, -0.15, -1.1]];",
                                                                                     "const VIEW = [[3.0, 1.6, -3.9], [0.22, -0.15, -1.1]];").replace(
    "const dir = camera.position.clone().sub(controls.target).normalize();",
    "const dir = b.dataset.v ? new THREE.Vector3(...b.dataset.v.split(',').map(Number)).normalize() : camera.position.clone().sub(controls.target).normalize();")


def rd(name):
    with open(os.path.join(s5.OUT, name), encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter=";"))[1:]


BODY = r"""<h1>Trap stalowy 2,5 × 0,63 m – lekki i tani, chodnik z lewej (S5)</h1>
<p class="lede">Wszystko skręcane, bez spawania. 4 rury pod koło 100×40×2 ze stali S355, chodnik tylko po lewej stronie (od strony stopki – stąd pchasz motocykl),
chodnik 340 mm, poprzeczki i siatka 630 mm. Model pokazuje każdy otwór, śrubę, tuleję i sworzeń dokładnie w miejscu z tabel otworów. Kliknij element, otwór albo śrubę, żeby zobaczyć wymiary.</p>
<div id="stage"><div class="hint" id="hint">Wczytuję model…</div><div id="tip"></div>
  <div id="info" role="dialog" aria-live="polite"><button class="x" id="ix" aria-label="Zamknij opis">✕</button><b id="it"></b><span id="ib"></span></div></div>
<div class="bar">
  <button id="b-roz" aria-pressed="true">Rozłożony</button><button id="b-anim" aria-pressed="false">▶ Składanie</button><button id="b-tr" aria-pressed="false">Do jazdy</button>
  <label for="pos">pozycja</label><input id="pos" type="range" min="0" max="1" step="0.002" value="0">
</div>
<div class="bar">
  <button data-f="A:pinTr:1" data-v="1,0.3,-0.6">Zawias przy przyczepie</button><button data-f="A:pinMid:-1" data-v="-1,0.2,-0.4">Zawias środkowy</button><button data-f="A:M8x:340:+125">Skrzyżowanie</button>
  <button data-f="A:M12oko:1" data-v="1,-0.25,-0.6">Sprężyna lewa</button><button data-f="A:M12oko:-1" data-v="-1,-0.25,-0.6">Sprężyna prawa</button><button data-f="B:P:650">Poprzeczka B2</button><button data-f="A:pinMid:chodnik" data-v="1,0.2,-0.4">Zawias chodnika</button><button id="b-all">Cały trap</button>
</div>
<div class="bar">
  <button class="lay" data-k="śruba" aria-pressed="true">Śruby</button><button class="lay" data-k="tuleja" aria-pressed="true">Tuleje</button>
  <button class="lay" data-k="siatka" aria-pressed="true">Siatka</button><button class="lay" data-k="przyczepa" aria-pressed="true">Przyczepa</button>
  <button id="b-x" aria-pressed="false">Profile przezroczyste</button><button id="b-drill" aria-pressed="false">Tylko otwory</button>
</div>
<div class="legend"><span><i style="background:#8a96a3"></i>rury jezdne S355 100×40×2</span><span><i style="background:#b9c0c8"></i>podłużnice chodnika 100×40×1,5</span>
<span><i style="background:#c9a77a"></i>poprzeczki 60×40×3 (na płasko)</span><span><i style="background:#3f6fb0"></i>prowadnice 40×40×3</span><span><i style="background:#3a3a3a"></i>płyty H / Z / S</span>
<span><i style="background:#b04a3a"></i>wsporniki K</span><span><i style="background:#e01b1b"></i>otwory</span><span><i style="background:#a9afb6"></i>śruby</span><span><i style="background:#d4b030"></i>tuleje</span></div>
<h2>W liczbach</h2>
<div class="kv">%KV%</div>
<h2>Drogi sił – co sprawdziłem i co poprawiłem</h2>
<div class="card"><p style="margin:0 0 8px">Policzyłem cały pokład jako <b>ruszt</b>: każda rura i poprzeczka to belka, każde skrzyżowanie to jedna śruba M8,
która przenosi docisk (rura naciska na poprzeczkę) albo rozciąganie (poprzeczka „wisi” na rurze). Podpory: sworznie przy przyczepie, ziemia pod końcem B
(tylko docisk – koniec może się oderwać), zawias środkowy tylko tam, gdzie są płyty Z. 36 położeń koła i stopy, obciążenia obliczeniowe.</p>
%SILY%
<p style="margin:10px 0 6px"><b>Co było źle:</b> rury chodnika kończyły się na zawiasie bez podpory, a sekcja B miała jedną poprzeczkę i słabą listwę T na nitach.
Stopa na krawędzi chodnika przy zawiasie obracała rurę B na tej jednej poprzeczce (koniec przy ziemi się odrywał) – w obliczeniach to <b>mechanizm</b>, w praktyce
uginający się chodnik trzymany tylko przez siatkę. Poprzeczki „wiszą” na śrubach przy rurach L1/L3 z siłą do 14 kN, a ścianka 2 mm pod podkładką M8 przenosi ok. 5 kN.</p>
<p style="margin:0"><b>Poprawka:</b> 2. poprzeczka w B (s = 650) zamiast listwy T; krawędź chodnika ma własny zawias (płyta Z + sworzeń Ø20 na tej samej osi);
2 oparcia chodnika z gumą na przyczepie; poprzeczki ze ścianką 3 mm. Waga: ok. +7 kg, a podnoszenie ze sprężynami Ø28 rośnie do %LIFT% kg.</p>
<img src="data:image/png;base64,%SILYPNG%" alt="Siła w śrubach skrzyżowań przed i po poprawce" style="width:100%;margin-top:10px;border-radius:8px">
<p class="note">Słupki: największe rozciąganie śruby w 10 najbardziej obciążonych skrzyżowaniach; linie przerywane: nośność ścianki poprzeczki pod podkładką. Dane: stal_S5/sily_S5.csv, model: sily.py.</p></div>
<h2>Odchudzenie i tańsze części</h2>
<div class="card">%OPT%
<p class="note">Rury jezdne zostają 100×40×2 S355 – pod oponą o śladzie ~100 mm całe tylne koło może stanąć na jednej rurze (%P_LANE%), więc tu nie da się ująć bez utraty zapasu.
Poprzeczka przy węższym chodniku pracuje lżej (%P_CROSS% zamiast %P_CROSS0%). Pojedyncza płyta zawiasu: śruba M12 jednocięta %P_M12%, skręcanie rury %P_TORS%.</p></div>
<h2>Co zmieniłem, żeby stal była lekka</h2>
<div class="card">%CMP%
<p class="note">Lewa strona = patrząc od ziemi na przyczepę. Prawa rura jezdna jest krawędzią trapu – prowadnica nad nią trzyma koło, a przy prowadzeniu stoisz po lewej, na chodniku.
Pas koła (282 mm między prowadnicami) jest w osi przyczepy, tak jak w wersji aluminiowej.</p></div>
<h2>Do czego są prowadnice (niebieskie kątowniki)</h2>
<div class="card"><p style="margin:0 0 8px">Pokład ma dwie strefy o różnej nośności: <b>pas koła</b> (4 rury S355, 282 mm między prowadnicami) i <b>siatkę</b> poza nim,
liczoną tylko na stopę (105 kg). Koło obliczeniowo daje 6,0 kN, stopa 2,3 kN – 2,6 raza mniej. Prowadnice to <b>krawężniki</b>, które fizycznie trzymają koło na pasie, który je udźwignie:</p>
<ul><li><b>Prawa</b> stoi na krawędzi trapu (nad prawą rurą L1). Bez niej koło zsuwa się z trapu nawet z wysokości 455 mm – motocykl przewraca się.</li>
<li><b>Lewa</b> oddziela koło od siatki chodnika (przęsło 140 mm między lewą rurą L1 a C1) i od Twoich stóp.</li>
<li>Pchasz 350 kg pod górę z boku i nie widzisz koła – prowadnice korygują tor bez Twojej siły.</li>
<li>Przy okazji dociskają siatkę do rur jezdnych (śruby M8 przez rurę z tuleją).</li></ul>
<p class="note">Wysokość 37 mm nad siatką łapie bok opony (opona do 240 mm – np. tylna Fat Boya – luz min. 21 mm na stronę), a jest za niska, żeby zaczepić podnóżek lub stopkę i da się ją przekroczyć.
G1 zaczyna się 150 mm od przyczepy: w pozycji do jazdy pokład stoi 15 mm za krawędzią podłogi, a góra prowadnicy wchodzi 28 mm nad podłogę – przy s = 0 zahaczałaby o krawędź podłogi.
G2 kończy się 530 mm przed ziemią, gdzie trap jest już tylko ~100 mm nad ziemią: to strefa wjazdu – koło ustawiasz swobodnie, zanim wejdzie między prowadnice.</p></div>
<h2>Siła przy podnoszeniu i opuszczaniu</h2><div class="card">%CHART%
<p class="note">Siła prostopadle do trapu na końcu sekcji A (przy zawiasie środkowym). Ujemny kąt = trap leży na ziemi, 90° = pion. Sprężyny %SPR% dobrane tak, żeby rozłożony trap
zawsze leżał na ziemi (nie podnosi się sam), a w pionie nie pchał w stronę przyczepy.</p></div>
<h2>Obliczenia (motocykl 350 kg + kierowca 105 kg)</h2>
<div class="card">%CALC%
<p class="note">Koło 273 kg ×1,5 (dynamika) ×1,5; stopa 105 kg ×1,5 ×1,5; ciężar własny ×1,35. Ręczne obliczenia w stylu EN 1993 / EN 1999, nie MES. Najbardziej wytężone: %WORST%.
Rury jezdne MUSZĄ być ze stali S355 (S355J2H / S355MH) – z S235 przy ściance 2 mm nie przechodzą. Zamiennik: 100×40×3 S235 (ok. +20 kg).</p></div>
<h2>Montaż i użytkowanie</h2><div class="card"><ul style="list-style:none;padding-left:0">%STEPS%</ul></div>
<h2>Ile wolno się pomylić (tolerancje)</h2><div class="card">%TOL%
<p class="note">Wytrzymałość ma zapas ok. 2,5 × rzeczywistego ciężaru do granicy plastyczności. Najgroźniejsza pomyłka materiałowa: rury jezdne z S235 zamiast S355 (wytężenie 82 % → ok. 124 %) – dlatego atest i żółte końce.
Obie rury L1 są identyczne – nie da się ich zamienić.</p></div>
<h2>Lista kontrolna</h2><div class="card"><p style="margin:0 0 6px"><b>Przed wjazdem / zjazdem</b></p><ul>%CHK1%</ul>
<p style="margin:10px 0 6px"><b>Przed jazdą</b></p><ul>%CHK2%</ul>
<p class="note">Druga blokada do jazdy: pas z grzechotką 25 mm (LC 400 daN) opasujący złożony trap na poprzeczce P, haki do uch z przodu przyczepy. Trzyma trap także wtedy,
gdy sworznie Ø12 zostaną w kieszeni (wytężenie 21 %). Do wydruku: stal_S5/lista_kontrolna_S5.pdf.</p></div>
<h2>Części</h2><div class="card">%BOM%</div>
<h2>Śruby, sworznie, tuleje</h2><div class="card">%BOLTS%
<p class="note">8.8 ocynk z podkładkami, nakrętki samohamowne. M8 20 N·m, M12 40 N·m. Sworznie zawiasów Ø20 z podkładką i zawleczką – nic nie dokręcasz.</p></div>
<h2>Otwory – miejsca wiercenia (%NHOLES%)</h2><div class="card" id="holes">%HOLES%
<p class="note">s – od końca sekcji (A: przy przyczepie, B: przy zawiasie środkowym), x – od osi pasa koła (x &gt; 0 = lewa, chodnik), z – od spodu rury.
Otwór przechodzący przez kilka części wierć razem albo przez płytę jako szablon. Model sprawdza, że każda śruba przechodzi przez otwory we wszystkich częściach, bez kolizji z materiałem.</p></div>
<h2>Zakupy</h2><div class="card">%BUY%
<p class="note">Orientacyjny koszt materiału z cynkowaniem: ok. %COST% zł netto (ceny-założenia w stal.py, sprawdź w swojej hurtowni).</p></div>
<h2>Pliki</h2><div class="card"><p>W repozytorium, katalog trap_uproszczony/stal_S5: rysunki_trap_S5.pdf (karty każdej rury z tabelą otworów, przekrój, widok z góry, zawiasy, płyty, obliczenia),
szablony_1do1_S5.pdf, DXF płyt, lista_czesci.csv, lista_srub.csv, lista_zakupow.csv, obliczenia.csv, otwory_z_modelu.csv, trap_s5.glb. lista_kontrolna_S5.pdf. Wszystko generuje skrypt stal_s5.py.</p></div>
</main>
"""


def main():
    M, summ = s5.main()
    glb = base64.b64encode(open(os.path.join(s5.OUT, "trap_s5.glb"), "rb").read()).decode()
    mA, mB, spr, lift, lift0, rows = s5.mA, s5.mB, s5.SPR, s5.LIFT, s5.LIFT0, s5.ROWS
    worst = max((r for r in rows if not r["nazwa"].startswith("[INFO]")), key=lambda r: r["wytezenie"])
    kinds = dict(M.bolt_axes)
    n_holes, n_join = len(M.hole_dia), len(M.bolt_axes)
    cost = round(sum(c[1] for c in stal.cost(s5.V, mA, mB, spr)))
    v_old = stal.VARIANTS["S5"]
    (oA, oAs, oAz), (oB, oBs, oBz) = stal.masses(v_old)
    o_spr, _ = stal.pick_springs(oA, (oAs, oAz), oB, (oBs, oBz))
    o_cost = round(sum(c[1] for c in stal.cost(v_old, oA, oB, o_spr)))
    o_rows = stal.calcs(v_old, oA, oB, o_spr["F1_N"])
    o_worst = max(o_rows, key=lambda r: r["wytezenie"])
    o_spr_zl = o_spr["sztuk"] * stal.CENY["sprezyna_40" if o_spr["F1_N"] > 2500 else "sprezyna_28"]
    spr_zl = spr["sztuk"] * stal.CENY["sprezyna_40" if spr["F1_N"] > 2500 else "sprezyna_28"]

    def pct(rws, start):
        return f'{next(r for r in rws if r["nazwa"].startswith(start))["wytezenie"] * 100:.0f} %'
    pcts = {"%P_LANE%": pct(rows, "Rura jezdna – zginanie, całe koło"), "%P_CROSS%": pct(rows, "Poprzeczka"), "%P_CROSS0%": pct(o_rows, "Poprzeczka"),
            "%P_M12%": pct(rows, "Zawias środkowy: śruba M12"), "%P_TORS%": pct(rows, "Rura jezdna zewnętrzna – skręcanie")}
    sp_txt = f"2 × {spr['F1_N']} N (Ø28)"
    kv = [(f"2,5 × {s5.WID / 1000:.2f} m".replace(".", ","), "trap rozłożony, 2 sekcje po 1,25 m"),
          (f"~{mA + mB:.0f} kg", f"trap (A {mA:.0f} kg, B {mB:.0f} kg); pierwsza wersja S5: {oA + oB:.0f} kg"),
          (f"~{max(r['user_kg'] for r in lift0):.0f} kg", f"podnoszenie bez sprężyn; ze sprężynami {spr['max_wysilek_kg']:.0f} kg"),
          (f"{g.ALPHA:.1f}°".replace(".", ","), f"kąt przy podłodze {g.H_FLOOR / 10:.0f} cm"),
          (f"{worst['wytezenie'] * 100:.0f}%", "najbardziej obciążona część"),
          (f"{n_holes} / {n_join}", "otwory / złącza w modelu, 0 kolizji"),
          (f"~{cost} zł", f"materiał z cynkowaniem; było {o_cost} zł")]
    kv_html = "".join(f"<div><b>{E(a)}</b><span>{E(b)}</span></div>" for a, b in kv)
    opt_rows = [["szerokość / chodnik", "740 mm / 450 mm", f"{s5.WID:.0f} mm / 340 mm (C1 x +{s5.XW:.0f}, C2 x +{s5.XE:.0f})"],
                ["płyty zawiasów H i Z", "po 2 na rurę (12 szt.)", "po 1 na rurę, z zewnątrz (8 szt., w tym 2 na krawędzi chodnika)"],
                ["poprzeczki", "3 × 60×40×2 + listwa T 40×5 na nitach", "4 × 60×40×3 (druga w sekcji B zamiast listwy)"],
                ["sworznie zawiasów", "M20×110, nakrętka niedokręcona", "Ø20 ISO 2341-B + zawleczka (krótsze, nic nie regulujesz)"],
                ["sprężyny gazowe", f"{o_spr['sztuk']} × {o_spr['F1_N']} N Ø40, oś M16 (ok. {o_spr_zl:.0f} zł)", f"{sp_txt}, oś M12 (ok. {spr_zl:.0f} zł)"],
                ["masa trapu", f"{oA + oB:.1f} kg".replace(".", ","), f"{mA + mB:.1f} kg".replace(".", ",")],
                ["podnoszenie ze sprężynami", f"{o_spr['max_wysilek_kg']:.0f} kg", f"{spr['max_wysilek_kg']:.0f} kg"],
                ["koszt materiału z cynkiem", f"{o_cost} zł", f"{cost} zł"],
                ["najbardziej obciążona część", f"{o_worst['wytezenie'] * 100:.0f} % ({o_worst['nazwa']})", f"{worst['wytezenie'] * 100:.0f} % ({worst['nazwa']})"]]
    cmp_rows = [["szerokość", "1190 mm, chodnik po obu stronach", f"{s5.WID:.0f} mm, chodnik 340 mm tylko z lewej"],
                ["rury jezdne (4 szt.)", "100×40×3 Al 6082-T6", "100×40×2 stal S355J2H"],
                ["podłużnice chodnika", "4 na sekcję, 100×40×2 Al", "2 na sekcję, 100×40×1,5 stal S235"],
                ["poprzeczki / prowadnice", "60×40×4 Al (na płasko) / kątownik 40×40×4 Al", "4 × 60×40×3 stal / kątownik 40×40×3 stal"],
                ["siatka", "Al, 1190 × 2500", f"stal ocynk ~4 kg/m², {s5.WID:.0f} × 2500 (1 arkusz)"],
                ["sprężyny gazowe", "2 × 1600 N (Ø28), obie przy chodnikach", f"{sp_txt}, oś M12; prawa na prawej rurze jezdnej L1"],
                ["wsporniki K na belce", "4", "3 (prawy zawiasowy trzyma też sprężynę)"],
                ["masa", "~67 kg", f"~{mA + mB:.0f} kg (stal na pełną szerokość: 150 kg grube ścianki / 114 kg cienkie)"]]
    steps = s5.STEPS
    steps_html = "".join(f"<li><b>{E(t)}</b><ul>" + "".join(f"<li>{E(x)}</li>" for x in xs) + "</ul></li>" for t, xs in steps)
    calc_rows = [[f'{E(r["nazwa"].replace("[INFO] ", ""))}<span class="note">{E(r["uwagi"])}</span>', f'{r["obciazenie"]:g} / {r["nosnosc"]:g} {E(r["jedn"])}',
                  pill(r["wytezenie"], r["nazwa"].startswith("[INFO]"))]
                 for r in rows]
    bom_rows = [[f"<b>{E(b[0])}</b> {E(b[1])}<span class='note'>{E(b[3])} · {E(b[7])}</span>", b[2], E(b[4]), b[5]] for b in rd("lista_czesci.csv")]
    bolt_rows = [[E(a), E(b) + f'<span class="note">{E(d)}</span>', c] for a, b, c, d in rd("lista_srub.csv")]
    hole_rows = [[i, f"Ø{p3.fmt(M.hole_dia[k])}", E(kinds.get(k, "–")), "<br>".join(E(t) for t in M.hole_txt[k])]
                 for i, k in enumerate(sorted(M.hole_dia, key=lambda k: (M.hole_txt[k][0])), 1)]
    buy_rows = [[E(a), E(b), E(c)] for a, b, c in rd("lista_zakupow.csv") if a]
    page = HEAD + BODY + TAIL
    for k, v in {"%KV%": kv_html, "%CMP%": table(["", "aluminium V2", "stal S5"], cmp_rows), "%CHART%": chart(lift, lift0),
                 "%SILY%": table(["", "przed poprawką", "po poprawce"], [
                     ["ugięcie chodnika pod stopą (najgorsze miejsce)", "mechanizm – brak podparcia (trzyma tylko siatka)" if -s5.SILY['przed']['walk'] > 100 else f"{-s5.SILY['przed']['walk']:.0f} mm", f"{-s5.SILY['po']['walk']:.1f} mm".replace(".", ",")],
                     ["ugięcie pod kołem (najgorsze miejsce)", f"{-s5.SILY['przed']['lane']:.1f} mm".replace(".", ","), f"{-s5.SILY['po']['lane']:.1f} mm".replace(".", ",")],
                     ["największa siła w śrubie skrzyżowania", f"{s5.SILY['przed']['tmax'][1][0] / 1e3:.1f} kN".replace(".", ","),
                      f"{s5.SILY['po']['tmax'][1][0] / 1e3:.1f} kN".replace(".", ",")],
                     ["nośność ścianki poprzeczki pod podkładką", f"{s5.face_NRd(235, 2.0, 60, 16) / 1e3:.1f} kN (2 mm)".replace(".", ","),
                      f"{s5.face_NRd(235, 3.0, 60, 16) / 1e3:.1f} kN (3 mm)".replace(".", ",")]]),
                 "%SILYPNG%": base64.b64encode(open(os.path.join(s5.OUT, "sily_sruby_S5.png"), "rb").read()).decode(),
                 "%LIFT%": f"{spr['max_wysilek_kg']:.0f}", "%OPT%": table(["", "było (S5)", "jest (S5 lekki i tani)"], opt_rows), "%SPR%": E(sp_txt),
                 "%CALC%": table(["Sprawdzenie", "Obciążenie / nośność", "Wytężenie"], calc_rows, (1, 2)), "%WORST%": E(worst["nazwa"]),
                 "%STEPS%": steps_html, "%BOM%": table(["Część", "Szt.", "Wymiar [mm]", "kg/szt."], bom_rows, (1, 3)),
                 "%BOLTS%": table(["Rozmiar", "Rodzaj / gdzie", "Szt."], bolt_rows, (2,)),
                 "%HOLES%": table(["Nr", "Ø", "Złącze", "Miejsce wiercenia w każdej części, przez którą przechodzi"], hole_rows, (0, 1)),
                 "%NHOLES%": str(n_holes), "%TOL%": table(["Co", "Tolerancja", "Jak to osiągnąć"], [[E(a), f"<b>{E(b)}</b>", E(c)] for a, b, c in s5.TOL]),
                 "%CHK1%": "".join(f"<li>☐ {E(x)}</li>" for x in s5.CHECK_BEFORE_LOAD), "%CHK2%": "".join(f"<li>☐ {E(x)}</li>" for x in s5.CHECK_BEFORE_DRIVE), "%BUY%": table(["Pozycja", "Ilość", "Uwagi"], buy_rows), "%COST%": str(cost), **pcts, "%GLB%": glb}.items():
        page = page.replace(k, v)
    out = os.path.join(s5.OUT, "trap_s5_strona.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(out, f"{len(page) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
