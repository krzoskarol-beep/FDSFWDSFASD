# Trap S5 – analizy dodatkowe (sprężyny, ergonomia, jazda, motocykl, zgniecenia)

Wygenerowane przez `analizy_dodatkowe.py`. Dane wejściowe: model S5 (masa, środek masy, krzywa podnoszenia), karta producenta motocykla (H-D, Model Year 2024 Fat Boy 114 – specifications (h-dmediakit.com)), dane producentów sprężyn gazowych (3,6 % na 10 °C), EN ISO 13854.

## 1. Sprężyny gazowe: temperatura, tolerancja, awaria

Nominalnie 2 × 2500 N (Ø28) przy 20 °C.

| przypadek | siła [N] | podnoszenie max [kg] | rozłożony trap | trap w pionie |
|---|---|---|---|---|
| -20 °C, siła nominalna | 2140 | 26,5 | -210 N·m – leży | 20 N·m – OK |
| -20 °C, siła −5 % | 2033 | 27,7 | -230 N·m – leży | 16 N·m – OK |
| -20 °C, siła +5 % | 2247 | 25,4 | -190 N·m – leży | 24 N·m – OK |
| +0 °C, siła nominalna | 2320 | 24,6 | -176 N·m – leży | 26 N·m – OK |
| +20 °C, siła nominalna | 2500 | 22,7 | -142 N·m – leży | 33 N·m – OK |
| +40 °C, siła nominalna | 2680 | 20,7 | -108 N·m – leży | 39 N·m – OK |
| +50 °C, siła nominalna | 2770 | 19,8 | -92 N·m – leży | 42 N·m – OK |
| +50 °C, siła −5 % | 2632 | 21,3 | -118 N·m – leży | 37 N·m – OK |
| +50 °C, siła +5 % | 2909 | 18,3 | -66 N·m – leży | 47 N·m – OK |
| jedna sprężyna zepsuta (20 °C) | 2500 | 36,1 | -377 N·m – leży | -12 N·m – OK |
| obie zepsute / zdjęte | 0 | 50,3 | -612 N·m – leży | -56 N·m – OK |

- W mrozie −20 °C podnoszenie rośnie do **27,7 kg**. W upale (+50 °C) rozłożony trap nadal leży.
- Gdy jedna sprężyna padnie, podnoszenie rośnie do **36,1 kg**. Trap nie spada, bo sprężyna tylko pomaga, a trzymają sworznie. Wymieniaj sprężyny parami co ok. 5 lat albo gdy jedna słabnie.

## 2. Ergonomia podnoszenia – równanie NIOSH (1991)

Ręka na końcu sekcji A. V to wysokość dłoni z geometrii, H = 40 cm (trap przed sobą), D = 120 cm, uchwyt „dostateczny” (CM 0,95), rzadkie podnoszenie (FM 1). To ocena przesiewowa, bo ruch jest obrotem, a nie czystym podnoszeniem.

- **Ze sprężynami:** największy wskaźnik **LI = 2,36** przy kącie 45° (siła 22,7 kg, dłonie na 135 cm, zalecana granica RWL 9,6 kg).
- **Bez sprężyn:** LI = 5,16.
- LI ≤ 1: brak ryzyka; 1–3: ryzyko podwyższone (dla zdrowej, wprawnej osoby, z techniką); > 3: wysokie.
- Wniosek: dwa **uchwyty** (uchwyt dobry, CM 1,0) i podnoszenie przodem do trapu obniżają LI o ok. 5 %. Sprężyny Ø40 2 × 2800 N obniżyłyby siłę do ok. 20 kg, czyli LI o ok. 15 %.

## 3. Trap złożony w czasie jazdy

Środek masy złożonego trapu jest 139 mm za tylną ścianą belki i 697 mm nad podłogą. Oś zawiasu jest 40 mm za belką, a sworzeń blokady 30 mm za osią. Współczynnik obciążenia 1,5.

| przypadek | moment wokół osi [N·m] | sworzeń blokady [kN] | sworzeń zawiasu [kN] |
|---|---|---|---|
| podskok 2,0 g w pionie | 207 | 5,18 / 32,6 | 5,35 / 90,5 |
| hamowanie 0,8 g + ciężar | -390 | 9,74 / 32,6 | 9,78 / 90,5 |
| ruszanie / cofanie 0,5 g + ciężar | 439 | 10,96 / 32,6 | 10,99 / 90,5 |

- Najgorsze jest hamowanie: sworzeń blokady **34 %** nośności. Sworzeń Ø12 ma luz w otworze Ø13, więc na drodze trap stuka i wyrabia otwory (zmęczenie, hałas). Pas z grzechotką dociąga trap do jednej strony luzu i to stukanie usuwa. Pas zakładaj zawsze, nie tylko jako zapas.
- W zakręcie 0,66 kN działa wzdłuż sworzni i przenoszą to łby, podkładki i zawleczki. Zawleczki ze stali nierdzewnej, nowe co sezon.

## 4. Motocykl (Harley-Davidson Fat Boy 114, dane producenta)

- Kąt trapu 11,0°. Na krawędzi podłogi motocykl traci prześwit **80 mm** (rozstaw osi / 2 × tg(α/2)). Zapas wynosi **35 mm** ze 115 mm prześwitu statycznego. Z kierowcą na siodle zawieszenie siada o ok. 20–30 mm i zapas spada prawie do zera, dlatego **wprowadzaj motocykl bez kierowcy, pchając**.
- Szerokość pasa 282 mm: tylna opona 240 mm ma luz **21 mm** na stronę, przednia 160 mm – 61 mm. Trzeba celować, ale się mieści.
- Masa 317 kg (gotowy do jazdy) < 350 kg przyjętych w obliczeniach ✅.

## 5. Miejsca zgniecenia (EN ISO 13854: palec 25 mm, dłoń 100 mm, stopa 120 mm, palce stopy 50 mm)

| miejsce | szczelina | wymagane | ocena | co zrobić |
|---|---|---|---|---|
| Styk rur A | B na zawiasie środkowym (góra) | 0 mm przy rozkładaniu | palec 25 / dłoń 100 | nie do spełnienia konstrukcyjnie (styk przenosi ściskanie) | chwyt tylko za uchwyty / rurę ≥ 250 mm od zawiasu; naklejka ISO 7010 W024 (zgniecenie dłoni) przy zawiasie |
| Pokład A ↔ tylny narożnik belki przy trapie w pionie | 15 mm (zmierzone w modelu) | palec 25 | za mało bez osłony | ODBOJNIK EPDM 11 mm na narożniku: zostaje 4 mm do rur i 1 mm do siatki (model 3D) – palec nie wejdzie ✅ |
| Płyta H ↔ tylna ściana belki w trakcie obrotu (60–85 % ruchu) | 5 mm (zmierzone w modelu) | ≤ 4 albo ≥ 25 | opuszek palca może wejść | ryzyko resztkowe: naklejka W024 na belce, ręce z dala od zawiasów przy przyczepie ⚠ |
| Płyta H ↔ wspornik K (oś zawiasu przy przyczepie) | 1 mm | palec 25 | szczelina ≤ 4 mm – palec nie wejdzie (EN ISO 13857) | bez zmian |
| Sekcja B wlecze się po ziemi (koniec ze skosem) | 0 mm do podłoża | palce stopy 50, stopa 120 | stopa pod końcem B | stać z boku, nie przed końcem B; buty z noskiem |
| Sprężyna gazowa: tłoczysko / oczko przy wsporniku K | zmienna | palec 25 | ręka na sprężynie przy składaniu | nie chwytać za sprężyny; przy przeglądzie tylko trap zablokowany sworzniami |

## 6. Przewidywania do protokołu badań (obciążenie charakterystyczne, bez współczynników)

| punkt | obciążenie | ugięcie z modelu [mm] | skok na styku [mm] |
|---|---|---|---|
| P1 | koło 273 kg na L2 (x +45), środek A (s = 600) | 1,2 | -0,3 |
| P2 | koło 273 kg na L2 przy zawiasie (A, s = 1250) | 5,1 | -1,9 |
| P3 | koło 273 kg na L4 w środku B (s = 600) | 1,1 | -0,1 |
| P4 | stopa 105 kg na C2 przy zawiasie (A, s = 1250) | 2,7 | -0,0 |
| P5 | stopa 105 kg na C2 w środku A (s = 600) | 1,3 | -0,0 |
| P6 | stopa 105 kg na C3 krawędź, środek B (s = 600) | 1,7 | 0,0 |

Pomiar: czujnik zegarowy na statywie, ugięcie względem podpór (sworznie przy przyczepie i koniec na ziemi). Kryteria i formularz: `protokol_badan_S5.pdf`.
