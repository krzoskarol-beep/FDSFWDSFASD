# Trap S5 – co zrobiłby najlepszy specjalista (i co z tego jest zrobione)

## 1. O co nikt nie zapytał, a specjalista by sprawdził

| temat | co wyszło | stan |
|---|---|---|
| Sprężyny w mrozie i upale (3,6 % siły na 10 °C), tolerancja ±5 %, awaria jednej | −20 °C: 27,7 kg; jedna sprężyna padła: 36 kg. Pierwotny otwór w K nie spełniał warunku w upale (+50 °C) | otwór w K przesunięty 30 → 35 mm: 22,7 kg w 20 °C, warunki spełnione od −20 do +50 °C ✅ |
| Ergonomia podnoszenia (równanie NIOSH) | wskaźnik LI ≈ 2,4: ryzyko podwyższone (> 1), ale nie wysokie (< 3); bez sprężyn LI 5,2 | zimą lub przy słabszej sprężynie podnosić we dwóch ⚠ |
| Trap złożony w czasie jazdy: podskoki 2 g, hamowanie 0,8 g, zakręt 0,5 g | sworzeń blokady 9,7 kN (ok. 30 % nośności); luz w otworze daje stukanie | pas z grzechotką zakładać zawsze ✅ |
| Prześwit motocykla na krawędzi podłogi | Fat Boy: utrata 80 mm z 115 mm, zapas 35 mm; z kierowcą prawie zero | wprowadzać bez kierowcy ⚠ |
| Miejsca zgniecenia (EN ISO 13854) | styk rur na zawiasie (0 mm), krawędź podłogi (15 mm < 25 mm dla palca) | naklejki W024, zderzak na krawędzi podłogi ⚠ |
| Drogi sił w pokładzie (model rusztu) | mechanizm w chodniku, poprzeczki „wiszące” na śrubach | poprawione ✅ (wcześniej) |
| Złożenie do jazdy (kolizje) | nakrętki uderzały w drugą sekcję | poprawione ✅ (wcześniej) |
| FMEA | 16 wad, 5 z działaniem przy budowie lub użytkowaniu | `fmea_S5.md` |

## 2. Z jakich surowych materiałów korzysta specjalista

| materiał źródłowy | po co | stan |
|---|---|---|
| Karta producenta motocykla (H-D MY2024 Fat Boy 114) | masa 317 kg, rozstaw osi 1665 mm, prześwit 115 mm, opony 160 / 240 | użyte ✅ |
| Dane producentów sprężyn gazowych | zależność siły od temperatury | użyte ✅ |
| Teksty przepisów: PoRD (Dz.U. 2024 poz. 1251), warunki techniczne (Dz.U. 2024 poz. 502) | światła, rejestracja | użyte ✅ |
| EN ISO 13854 | szczeliny przeciw zgnieceniu | użyte ✅ |
| **Atesty 3.1 (EN 10204) kupionej stali** | rzeczywista granica plastyczności i grubość ścianki | przy zakupie ⚠ |
| **Tabela nośności siatki od dostawcy** | siatka liczona na stopę – przyjęte założenie | zapytać dostawcę ⚠ |
| **Pomiary Twojej przyczepy** (belka, wysokość podłogi, szerokość, lampy, masa) | wsporniki K, oparcia, wysięgniki, DMC, nacisk na hak | brak – pytanie do Ciebie ⚠ |
| **Karta katalogowa wybranej sprężyny** (F1, tolerancja, długości) | dokładna krzywa podnoszenia | przy zakupie ⚠ |

## 3. Narzędzia i metody

| metoda | gdzie w projekcie |
|---|---|
| Obliczenia ręczne w stylu EN 1993-1-1 / 1-3 / 1-8 (zginanie, docisk, ścinanie śrub, linie załomów ścianki) | `stal.py`, `stal_s5.py` |
| Model rusztu (metoda sztywności, 3 stopnie swobody w węźle, podpory jednostronne) | `sily.py` |
| Model 3D z kontrolą: każda śruba przechodzi przez otwory, brak kolizji po złożeniu | `podglad3d.py` |
| Optymalizacja geometrii sprężyn (przeszukanie siatki, ograniczenia od −20 do +50 °C) | `analizy_dodatkowe.py`, otwór w K (35; −100) |
| Równanie NIOSH, EN ISO 13854, FMEA | `analizy_dodatkowe.py`, `fmea_S5.md` |
| **Testy automatyczne**: model porównany ze wzorami z podręcznika i z równowagą sił | `testy/test_trap_s5.py` (9 testów) |
| Do zrobienia przez specjalistę: MES powłokowy węzłów (zawias środkowy, ścianka rury pod śrubami K i H), np. w Fusion Simulation albo Code_Aster | ⚠ |

Testy już znalazły dwa błędy:
- **model rusztu:** zawias liczony jako półsztywny, przez co ugięcia były zawyżone o 17 %;
- **geometria sprężyn:** pierwsze przeszukiwanie pomijało upał, więc wskazany otwór łamał warunek w pionie przy +40 °C.

## 4. Obiektywny dowód jakości (poza wynikiem AI)

1. **Próba prototypu wg `protokol_badan_S5.pdf`** (najmocniejszy dowód). Ugięcia z czujnika zegarowego w 6 punktach porównane
   z modelem (kryterium ≤ 1,3 × model); próba 1,5 × obciążenia bez trwałego odkształcenia; masa ±5 %; siła podnoszenia
   z wagi hakowej ±25 %; luz po złożeniu ≥ 8 mm ze szczelinomierza.
2. **Atesty 3.1 stali** i pomiar grubości ścianek suwmiarką.
3. **Testy automatyczne** (`python3 -m pytest testy`): wyniki porównane z rozwiązaniami podręcznikowymi, każdy może je powtórzyć.
4. **Niezależne sprawdzenie przez człowieka**: inżynier konstruktor (najlepiej z uprawnieniami) przelicza 3–4 najbardziej obciążone
   miejsca; rzeczoznawca samochodowy lub diagnosta ocenia zgodność z przepisami.
5. **Pozytywne badanie techniczne** w stacji kontroli pojazdów (przyczepa SAM z trapem).
6. **Ważenie** gotowego trapu i zestawu przyczepa + motocykl na wadze (DMC, nacisk na hak) – liczby, nie szacunki.
