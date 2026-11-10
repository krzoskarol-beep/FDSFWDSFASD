# Trap aluminiowy do przyczepki 2,5 × 1,19 m – wersja uproszczona (V2)

To nadal trap pod motocykl do 350 kg z kierowcą (koło 273 kg). Ma dwie sekcje po 1250 mm, które składają się na zawiasie środkowym. Jest przykręcony do tylnej belki przyczepy, a do jazdy staje pionowo jako klapa.

**Wszystko jest skręcane albo nitowane. Nie ma spawania ani gięcia.** Każdą płytę stalową tnie się prosto (to prostokąty), a wszystkie aluminiowe profile tnie się na długość.

## Pliki

| plik | co to jest |
|---|---|
| `rysunki_trap_v2.pdf` | Opis, przekrój, widok z góry, widok z boku (rozłożony i do jazdy), zawiasy, karta każdej rury z tabelą otworów, płyty, obliczenia i wykres siły przy podnoszeniu |
| `szablony_1do1_v2.pdf` | Płyty H, Z, S i wspornik K w skali 1:1. Drukuj w „rzeczywistym rozmiarze” i sprawdź kwadrat 50 mm |
| `DXF/` | Te same płyty w DXF, gdybyś jednak zamawiał cięcie laserem |
| `lista_czesci.csv`, `lista_srub.csv`, `lista_zakupow.csv` | Listy części, śrub i tulei oraz zakupów |
| `obliczenia.csv`, `trap_v2_dane.json` | Wszystkie kontrole wytrzymałości, masy i tabela podnoszenia |
| `generuj.py` | Skrypt, który to wszystko liczy i rysuje. Na górze są parametry: wysokość podłogi, rozstawy, obciążenia. Uruchomienie: `pip install matplotlib ezdxf` i `python3 generuj.py` |

## Co było nie tak / za trudne w poprzedniej wersji

1. **Za dużo różnych elementów.** Było 7 profili aluminiowych, 26 rodzajów części, 9 rodzajów tulei (169 sztuk) i 376 otworów.
2. **Ceowniki 50 mm na 30 tulejkach dystansowych D1.** To 30 luźnych kawałków, a każdy dokłada swoją tolerancję wysokości.
3. **Płyty o skomplikowanych kształtach.** Ośmiokątne ucha zawiasu Z1, Z2 i Z4 oraz wycinany wspornik M2 trudno dokładnie wyciąć szlifierką. Było 5 różnych płyt w zawiasie środkowym.
4. **Koniec sekcji B ściągnięty prętem M8×1210** przez 18 ścianek i z 18 nakrętkami. Ciężko to złożyć.
5. **Część śladu tylnej opony mogła stanąć na siatce na przęśle 100 mm.** Sam stary projekt to zaznaczał i wymagał tabeli nośności siatki pod koło.
6. Pod każdą prowadnicą koła musiała leżeć osobna podłużnica.

## Co zmieniłem

- **Koło jedzie zawsze po rurach.** Pod kołem leżą 4 rury 100×40×3 z **EN AW-6082-T6**, rozstawione na x = ±45 i ±125. Pas między prowadnicami ma 282 mm, a szczeliny między rurami 40–50 mm. Siatka niesie tylko stopy, a jej przęsła mają najwyżej 190 mm.
- **Wszystkie podłużnice mają 100 mm wysokości.** Leżą wprost na poprzeczkach 60×40×3, więc nie ma tulejek dystansowych.
- **Każde skrzyżowanie jest takie samo.** To śruba zamkowa M8×200 przez siatkę i **jedna** tuleja Ø12×1,5 dł. 159,5 na wylot przez podłużnicę i poprzeczkę.
- **Zawias środkowy to 8 identycznych prostokątów Z** (płaskownik 100×6, dł. 170) i sworzeń w postaci śruby M20×110 8.8.
  - Sworzeń jest 35 mm pod rurami. Po rozłożeniu górne krawędzie rur stykają się, więc zawias przenosi zginanie sam, bez żadnej blokady, której można by zapomnieć.
  - Sekcja B składa się w dół, pod sekcję A.
- **Zawias przy przyczepie to płyty H** (płaskownik 80×6, dł. 200) **i wspornik K** (odcinek kątownika 100×100×10, dł. 130).
  - Te same wsporniki K trzymają dolne oczka sprężyn gazowych.
  - Do jazdy blokuje się trap sworzniem Ø12 przez K i H.
- **Prowadnica koła to kątownik Al 40×40×4 położony na siatce** nad zewnętrzną rurą jezdną. Przykręca się go śrubą M8 w dół przez tę rurę, więc nie potrzeba osobnej podłużnicy.
- **Siatka jest w jednym kawałku na sekcję** i wycina się ją z jednego arkusza 1250×2500. Przykręcasz ją wkrętami samowiercącymi.
- **Koniec sekcji B ściąga płaskownik 40×5** przynitowany od spodu. Zastępuje pręt gwintowany.

| | poprzednio | teraz |
|---|---|---|
| profile Al | 7 | 5 |
| rodzaje części / sztuki (bez śrub) | 26 / 79 | 16 / 44 |
| otwory | 376 | 268 (+ drobne Ø4,9 pod nity) |
| rodzaje tulei / sztuki | 9 / 169 | 6 / 64 (na samym trapie 4 rodzaje) |
| płyty stalowe | 7 kształtów, wielokąty | 4 kształty, same prostokąty |
| masa trapu | 72,4 kg | **65 kg** (+ 7,8 kg wsporników K na przyczepie) |
| siła przy podnoszeniu ze sprężynami / bez | 24,6 / 40,1 kg | **18,6 / 36,1 kg** |

## Wyniki obliczeń

Pełna lista jest w `obliczenia.csv` i w PDF. Wszystkie wytężenia wychodzą poniżej 1,0.

| element | wytężenie |
|---|---|
| Rura jezdna 6082-T6, 75 % koła na jednej rurze | 0,66 |
| Ta sama rura, gdy całe koło stoi na jednej rurze (skrajny przypadek) | 0,88 |
| Ugięcie | 10,5 mm przy limicie 12,5 mm |
| Poprzeczka, gdy stopa stoi na samej krawędzi trapu | 0,84 |
| Zawias środkowy | 0,09–0,42 |
| Zawias przy przyczepie | 0,03–0,16 |

**Rura jezdna z „zwykłego” 6060 (PA38) nie przejdzie** (1,11). Rury jezdne muszą być z 6082-T6 (PA4).

Przyjęte obciążenia są takie jak w starym projekcie: koło 273 kg ×1,5 (dynamika) ×1,5, stopa 105 kg ×1,5 ×1,5, ciężar własny ×1,35. To ręczne obliczenia w stylu Eurokodu (EN 1999 i EN 1993), a nie analiza MES.

Sprężyny gazowe są te same co w starym projekcie: 2 × 460 mm, skok 200 mm, 1600 N.
- Rozłożony trap leży na ziemi z momentem 135 N·m, więc sprężyny go nie podniosą.
- W pionie trap jest prawie w równowadze (około +3 N·m), więc nie leci na człowieka.
- Sprężyna pracuje na długościach 280–375 mm i nie dochodzi do końca skoku.

## Kolejność budowy

1. **Przetnij profile.** Rury 1250 mm, poprzeczki 1190 mm, prowadnice 1095 i 715 mm.
   - W ośmiu podłużnicach sekcji B wytnij skos przy ziemi wyrzynarką. Skos ma 516 mm: utnij dno na 734 mm, a boki tnij ukośnie do górnej krawędzi na końcu.
2. **Wytnij płyty z płaskownika.** Płyty H i Z wierć **w pakiecie** (4 i 8 sztuk naraz, w imadle, na wiertarce stołowej), wtedy wszystkie będą identyczne.
3. **Wierć otwory w rurach według kart w PDF.**
   - Otwory pionowe przez rurę i poprzeczkę wierć na wiertarce stołowej albo z prowadnikiem, inaczej się rozjadą.
   - Otwory pod tuleje mają średnicę tulei + 0,5 mm (Ø12,5 i Ø18,5).
4. **Zawias środkowy.**
   - Połóż L1 i L3 czołami na równej podłodze, tak żeby górne krawędzie się stykały.
   - Przyłóż płyty Z, włóż sworzeń M20 i dopiero wtedy wierć otwory w rurach przez płyty jako szablon.
   - Płyty sekcji B idą na zewnątrz płyt A, na podkładkach 6 mm.
5. **Złóż ruszt każdej sekcji.** Do góry nogami na płaskiej podłodze: podłużnice, poprzeczki, tuleje i śruby M8 (dokręcić 20 N·m).
6. **Odwróć sekcję i połóż siatkę.**
   - Dłuższa przekątna oczka (LWD) ma iść w poprzek trapu.
   - Przykręć ją wkrętami co ok. 250 mm do każdej podłużnicy i połóż prowadnice.
7. **Wsporniki K.** Przykręć je do belki przyczepy, wsadź sworznie M20 i sprężyny.
   - Sworzni M20 nie dokręcaj na sztywno, mają się obracać.
8. **Zabezpiecz styki stali z aluminium.** Pod każdą płytę stalową daj pastę cynkową / Duralac i podkładki izolujące. Płyty ocynkuj (spray albo ogniowo).

## PRZED PIERWSZYM UŻYCIEM

1. **Policzone dla podłogi na 480 mm i przykładowej belki 50×75×3.** Podaj swoją wysokość podłogi, przekrój belki i szerokość skrzyni, a dopasuję wsporniki K, śruby do belki i kąt.
2. **Siatka niesie tylko stopy.** Dostawca powinien potwierdzić nośność na 160 kg w punkcie przy przęśle 190 mm.
3. **Próba obciążenia przed pierwszym wjazdem:** 400 kg (worki na palecie) przy zawiasie środkowym, nacisk przez klocek 10 × 10 cm:
   - (a) nad rurą wewnętrzną,
   - (b) nad rurą zewnętrzną,
   - (c) 50 mm od podłogi przyczepy.
   Po zdjęciu ciężaru nic nie może zostać wygięte, a górne krawędzie rur przy zawiasie mają się stykać bez szczeliny.
4. **Pierwszy wjazd bez kierowcy,** wpychając motocykl z pomocnikiem. Ładuj tylko z przyczepą podpiętą do auta (albo podpartą z tyłu).
5. **Po 3–5 wjazdach dokręć wszystkie śruby** i sprawdź styk rur przy zawiasie środkowym.

## Jak składać do jazdy

1. Chwyć trap za zawias środkowy i podnoś sekcję A. Sekcja B wlecze się po ziemi, a potem sama zawisa pod A.
2. Postaw trap pionowo.
3. Włóż 2 sworznie blokady Ø12 (przez wspornik K i płytę H).
4. Zapnij zapięcia (albo pas z grzechotką) między sekcjami.

Rozkładasz w odwrotnej kolejności. Nie trzymaj palców między sekcjami przy zawiasie środkowym.
