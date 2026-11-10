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


BODY = r"""<h1>Trap stalowy 2,5 × 0,74 m – optymalnie lekki, chodnik z lewej (S5)</h1>
<p class="lede">Wszystko skręcane, bez spawania. 4 rury pod koło 100×40×2 ze stali S355, chodnik tylko po lewej stronie (od strony stopki – stąd pchasz motocykl),
poprzeczki i siatka 740 mm. Model pokazuje każdy otwór, śrubę, tuleję i sworzeń dokładnie w miejscu z tabel otworów. Kliknij element, otwór albo śrubę, żeby zobaczyć wymiary.</p>
<div id="stage"><div class="hint" id="hint">Wczytuję model…</div><div id="tip"></div>
  <div id="info" role="dialog" aria-live="polite"><button class="x" id="ix" aria-label="Zamknij opis">✕</button><b id="it"></b><span id="ib"></span></div></div>
<div class="bar">
  <button id="b-roz" aria-pressed="true">Rozłożony</button><button id="b-anim" aria-pressed="false">▶ Składanie</button><button id="b-tr" aria-pressed="false">Do jazdy</button>
  <label for="pos">pozycja</label><input id="pos" type="range" min="0" max="1" step="0.002" value="0">
</div>
<div class="bar">
  <button data-f="A:pinTr:1" data-v="1,0.3,-0.6">Zawias przy przyczepie</button><button data-f="A:pinMid:-1" data-v="-1,0.2,-0.4">Zawias środkowy</button><button data-f="A:M8x:340:+125">Skrzyżowanie</button>
  <button data-f="A:M12oko:1" data-v="1,-0.25,-0.6">Sprężyna lewa</button><button data-f="A:M12oko:-1" data-v="-1,-0.25,-0.6">Sprężyna prawa</button><button data-f="B:T">Listwa T</button><button id="b-all">Cały trap</button>
</div>
<div class="bar">
  <button class="lay" data-k="śruba" aria-pressed="true">Śruby</button><button class="lay" data-k="tuleja" aria-pressed="true">Tuleje</button>
  <button class="lay" data-k="siatka" aria-pressed="true">Siatka</button><button class="lay" data-k="przyczepa" aria-pressed="true">Przyczepa</button>
  <button id="b-x" aria-pressed="false">Profile przezroczyste</button><button id="b-drill" aria-pressed="false">Tylko otwory</button>
</div>
<div class="legend"><span><i style="background:#8a96a3"></i>rury jezdne S355 100×40×2</span><span><i style="background:#b9c0c8"></i>podłużnice chodnika 100×40×1,5</span>
<span><i style="background:#c9a77a"></i>poprzeczki 60×40×2</span><span><i style="background:#3f6fb0"></i>prowadnice 40×40×3</span><span><i style="background:#3a3a3a"></i>płyty H / Z / S</span>
<span><i style="background:#b04a3a"></i>wsporniki K</span><span><i style="background:#e01b1b"></i>otwory</span><span><i style="background:#a9afb6"></i>śruby</span><span><i style="background:#d4b030"></i>tuleje</span></div>
<h2>W liczbach</h2>
<div class="kv">%KV%</div>
<h2>Co zmieniłem, żeby stal była lekka</h2>
<div class="card">%CMP%
<p class="note">Lewa strona = patrząc od ziemi na przyczepę. Prawa rura jezdna jest krawędzią trapu – prowadnica nad nią trzyma koło, a przy prowadzeniu stoisz po lewej, na chodniku.
Pas koła (282 mm między prowadnicami) jest w osi przyczepy, tak jak w wersji aluminiowej.</p></div>
<h2>Siła przy podnoszeniu i opuszczaniu</h2><div class="card">%CHART%
<p class="note">Siła prostopadle do trapu na końcu sekcji A (przy zawiasie środkowym). Ujemny kąt = trap leży na ziemi, 90° = pion. Sprężyny %SPR% dobrane tak, żeby rozłożony trap
zawsze leżał na ziemi (nie podnosi się sam), a w pionie nie pchał w stronę przyczepy.</p></div>
<h2>Obliczenia (motocykl 350 kg + kierowca 105 kg)</h2>
<div class="card">%CALC%
<p class="note">Koło 273 kg ×1,5 (dynamika) ×1,5; stopa 105 kg ×1,5 ×1,5; ciężar własny ×1,35. Ręczne obliczenia w stylu EN 1993 / EN 1999, nie MES. Najbardziej wytężone: %WORST%.
Rury jezdne MUSZĄ być ze stali S355 (S355J2H / S355MH) – z S235 przy ściance 2 mm nie przechodzą. Zamiennik: 100×40×3 S235 (ok. +20 kg).</p></div>
<h2>Montaż i użytkowanie</h2><div class="card"><ol>%STEPS%</ol></div>
<h2>Części</h2><div class="card">%BOM%</div>
<h2>Śruby, sworznie, tuleje</h2><div class="card">%BOLTS%
<p class="note">8.8 ocynk z podkładkami, nakrętki samohamowne. M8 20 N·m, M12 40 N·m, M16 60 N·m. Sworzni M20 nie dokręcaj na sztywno – mają się obracać.</p></div>
<h2>Otwory – miejsca wiercenia (%NHOLES%)</h2><div class="card" id="holes">%HOLES%
<p class="note">s – od końca sekcji (A: przy przyczepie, B: przy zawiasie środkowym), x – od osi pasa koła (x &gt; 0 = lewa, chodnik), z – od spodu rury.
Otwór przechodzący przez kilka części wierć razem albo przez płytę jako szablon. Model sprawdza, że każda śruba przechodzi przez otwory we wszystkich częściach, bez kolizji z materiałem.</p></div>
<h2>Zakupy</h2><div class="card">%BUY%
<p class="note">Orientacyjny koszt materiału z cynkowaniem: ok. %COST% zł netto (ceny-założenia w stal.py, sprawdź w swojej hurtowni).</p></div>
<h2>Pliki</h2><div class="card"><p>W repozytorium, katalog trap_uproszczony/stal_S5: rysunki_trap_S5.pdf (karty każdej rury z tabelą otworów, przekrój, widok z góry, zawiasy, płyty, obliczenia),
szablony_1do1_S5.pdf, DXF płyt, lista_czesci.csv, lista_srub.csv, lista_zakupow.csv, obliczenia.csv, otwory_z_modelu.csv, trap_s5.glb. Wszystko generuje skrypt stal_s5.py.</p></div>
</main>
"""


def main():
    M, summ = s5.main()
    glb = base64.b64encode(open(os.path.join(s5.OUT, "trap_s5.glb"), "rb").read()).decode()
    mA, mB, spr, lift, lift0, rows = s5.mA, s5.mB, s5.SPR, s5.LIFT, s5.LIFT0, s5.ROWS
    worst = max(rows, key=lambda r: r["wytezenie"])
    kinds = dict(M.bolt_axes)
    n_holes, n_join = len(M.hole_dia), len(M.bolt_axes)
    cost = next(x for x in json.load(open(os.path.join(s5.HERE, "stal_dane.json"), encoding="utf-8"))["warianty"]
                if x["klucz"] == "S5")["koszt"]
    sp_txt = f"2 × {spr['F1_N']} N (Ø40)"
    kv = [("2,5 × 0,74 m", "trap rozłożony, 2 sekcje po 1,25 m"),
          (f"~{mA + mB:.0f} kg", f"trap (A {mA:.0f} kg, B {mB:.0f} kg) + 3 wsporniki K 5,8 kg"),
          (f"~{max(r['user_kg'] for r in lift0):.0f} kg", f"podnoszenie bez sprężyn; ze sprężynami {spr['max_wysilek_kg']:.0f} kg"),
          (f"{g.ALPHA:.1f}°".replace(".", ","), f"kąt przy podłodze {g.H_FLOOR / 10:.0f} cm"),
          (f"{worst['wytezenie'] * 100:.0f}%", "najbardziej obciążona część"),
          (f"{n_holes} / {n_join}", "otwory / złącza w modelu, 0 kolizji"),
          (f"~{cost} zł", "materiał z cynkowaniem")]
    kv_html = "".join(f"<div><b>{E(a)}</b><span>{E(b)}</span></div>" for a, b in kv)
    cmp_rows = [["szerokość", "1190 mm, chodnik po obu stronach", "740 mm, chodnik tylko z lewej"],
                ["rury jezdne (4 szt.)", "100×40×3 Al 6082-T6", "100×40×2 stal S355J2H"],
                ["podłużnice chodnika", "4 na sekcję, 100×40×2 Al", "2 na sekcję, 100×40×1,5 stal S235"],
                ["poprzeczki / prowadnice", "60×40×3 Al / kątownik 40×40×4 Al", "60×40×2 stal / kątownik 40×40×3 stal"],
                ["siatka", "Al, 1190 × 2500", "stal ocynk ~4 kg/m², 740 × 2500 (1 arkusz)"],
                ["sprężyny gazowe", "2 × 1600 N (Ø28), obie przy chodnikach", f"{sp_txt}, oś M16; prawa na rurze jezdnej L1P"],
                ["wsporniki K na belce", "4", "3 (prawy zawiasowy trzyma też sprężynę)"],
                ["masa", "~72 kg", f"~{mA + mB:.0f} kg (stal z pełną szerokością: 150 kg grube ścianki / ~118 kg cienkie)"]]
    steps = [
        ("Zmierz przyczepę", ["Wysokość podłogi (liczona 480 mm), przekrój tylnej belki (w modelu 50×75×3) i gdzie ma stać trap – pas koła w osi przyczepy, chodnik w lewo.",
                              "Podeślij wymiary belki przed wierceniem wsporników K."]),
        ("Kup materiał", ["Według tabeli „Zakupy”. Rury jezdne tylko S355 – sprawdź atest/oznaczenie na sztandze."]),
        ("Przetnij", ["8 rur jezdnych i 4 podłużnice po 1250 mm, 3 poprzeczki 740 mm, listwa T 740 mm, kątowniki 1095 i 715 mm (po 2).",
                      f"W 6 podłużnicach sekcji B (L3, L4, C3) skos przy ziemi {g.SKOS:.0f} mm: dno krótsze, boki ukośnie."]),
        ("Płyty stalowe", ["Same prostokąty. H (4) i Z (8) wierć w pakiecie. Płyty S i wsporniki K: oczko sprężyny Ø17 (śruba M16).",
                           "Szablony 1:1: szablony_1do1_S5.pdf – drukuj 100 %, sprawdź kwadrat 50 mm."]),
        ("Otwory w rurach", ["Wg kart w rysunki_trap_S5.pdf. Uwaga: L1L (lewa) i L1P (prawa) różnią się – L1P ma 2 dodatkowe otwory Ø18,5 pod płytę S prawej sprężyny.",
                             "Otwór pod tuleję = Ø tulei + 0,5 mm (Ø12,5 / Ø18,5). Wiertarka stołowa albo prowadnik."]),
        ("Zawias środkowy", ["L1L/L1P i L3 czołami na równej podłodze, górne krawędzie stykają się. Płyty Z, sworzeń M20, dopiero wtedy wierć rury przez płyty."]),
        ("Cynkowanie", ["Wszystkie części stalowe cynkuj ogniowo PO wierceniu (albo podkład epoksydowy + farba). Potem przetrzyj otwory, tuleje wejdą luźno."]),
        ("Ruszt i siatka", ["Do góry nogami: podłużnice, poprzeczki, tuleje Ø12×1,5 dł. 159,5, M8×200 (20 N·m). Listwa T nitami pod sekcją B.",
                            "Odwróć, siatka na wkręty 4,8×19 co ~250 mm, prowadnice na siatce M8×130 nad rurami ±125."]),
        ("Na przyczepie", ["3 wsporniki K do belki. Sworznie M20 niedokręcone. Sprężyny: lewa C1 ↔ K sprężyny (x +369), prawa L1P ↔ K zawiasu (x −152).",
                           "Sprężyny zakładaj przy trapie w pionie (zablokowanym sworzniami)."]),
        ("Przed pierwszym użyciem", ["Próba 400 kg przy zawiasie środkowym nad każdą rurą jezdną – nic nie może zostać wygięte. Pierwszy wjazd bez kierowcy, przyczepa podpięta do auta.",
                                     "Po 3–5 wjazdach dokręć śruby."]),
    ]
    steps_html = "".join(f"<li><b>{E(t)}</b><ul>" + "".join(f"<li>{E(x)}</li>" for x in xs) + "</ul></li>" for t, xs in steps)
    calc_rows = [[f'{E(r["nazwa"])}<span class="note">{E(r["uwagi"])}</span>', f'{r["obciazenie"]:g} / {r["nosnosc"]:g} {E(r["jedn"])}', pill(r["wytezenie"])]
                 for r in rows]
    bom_rows = [[f"<b>{E(b[0])}</b> {E(b[1])}<span class='note'>{E(b[3])} · {E(b[7])}</span>", b[2], E(b[4]), b[5]] for b in rd("lista_czesci.csv")]
    bolt_rows = [[E(a), E(b) + f'<span class="note">{E(d)}</span>', c] for a, b, c, d in rd("lista_srub.csv")]
    hole_rows = [[i, f"Ø{p3.fmt(M.hole_dia[k])}", E(kinds.get(k, "–")), "<br>".join(E(t) for t in M.hole_txt[k])]
                 for i, k in enumerate(sorted(M.hole_dia, key=lambda k: (M.hole_txt[k][0])), 1)]
    buy_rows = [[E(a), E(b), E(c)] for a, b, c in rd("lista_zakupow.csv") if a]
    page = HEAD + BODY + TAIL
    for k, v in {"%KV%": kv_html, "%CMP%": table(["", "aluminium V2", "stal S5"], cmp_rows), "%CHART%": chart(lift, lift0), "%SPR%": E(sp_txt),
                 "%CALC%": table(["Sprawdzenie", "Obciążenie / nośność", "Wytężenie"], calc_rows, (1, 2)), "%WORST%": E(worst["nazwa"]),
                 "%STEPS%": steps_html, "%BOM%": table(["Część", "Szt.", "Wymiar [mm]", "kg/szt."], bom_rows, (1, 3)),
                 "%BOLTS%": table(["Rozmiar", "Rodzaj / gdzie", "Szt."], bolt_rows, (2,)),
                 "%HOLES%": table(["Nr", "Ø", "Złącze", "Miejsce wiercenia w każdej części, przez którą przechodzi"], hole_rows, (0, 1)),
                 "%NHOLES%": str(n_holes), "%BUY%": table(["Pozycja", "Ilość", "Uwagi"], buy_rows), "%COST%": str(cost), "%GLB%": glb}.items():
        page = page.replace(k, v)
    out = os.path.join(s5.OUT, "trap_s5_strona.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(out, f"{len(page) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
