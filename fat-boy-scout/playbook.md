# Playbook Fat Boy Scout

Pamięć agenta między przebiegami. Agent czyta ten plik na początku każdego przebiegu, a na końcu dopisuje lekcje.

## Lekcje
- 2026-11-12: Najwięcej trafień dają zapytania `site:facebook.com/marketplace/item` z pełną frazą rocznika („2018 Harley-Davidson Fat Boy”).
- 2026-11-12: `tbs: qdr:m` (ostatni miesiąc) przy `marketplace/item` zwraca śmieci, np. zabawki i części z Kalifornii. Nie używać.
- 2026-11-12: Zapytania o miasta Midwestu („Chicago OR Milwaukee…”) zwracają głównie stare Fat Boye (1990–2011). Mało przydatne, ale tańsze 114 pojawiają się w sekcji „related” innych ogłoszeń.
- 2026-11-12: Wiele ofert widać tylko jako „related items” przy innych ogłoszeniach albo na stronach kategorii miast (`/marketplace/<miasto>/harley-davidson/`). Wtedy nie ma bezpośredniego linku, więc trzeba dać link do strony, na której oferta była widoczna.
- 2026-11-12: Cena 1 234 USD to wypełniacz Facebooka, a nie prawdziwa cena (np. 2023 Fat Boy w Davenport, IA).
- 2026-11-12: Fat Boy 2021–2024 to zawsze 114. Rocznik 2020 i lata 2018–2019 bez kodu FLFBS albo „114” w ogłoszeniu oznaczać „114 niepotwierdzone” (FLFB = 107). Od 2025 silnik 117.
- 2026-11-12 (recenzja): zapytania oceniać po unikalnych trafieniach, bo kilka zapytań często znajduje tego samego Harleya. Ceny w indeksie to ceny ofertowe, a nie transakcyjne, więc ranking jest orientacyjny.
- 2026-11-12: Rynek (mediana z 40 ofert w USA): 2018 ok. 12 000 USD, 2020 ok. 13 900, 2022 ok. 15 500, 2024 ok. 19 500. Fat Boy 114 do 11 000 USD to rzadkość: 5 sztuk w całym kraju.

- 2026-11-12: Zapytanie o przebieg („<model> <miasto> miles”) znalazło przy okazji nową ofertę: 2018 FLFBS za 9 000 USD, 9,9 tys. mil, Vernon Rockville, CT. Fragmenty stron kategorii miast w CT i VA podają przebieg („26K miles”). Doszukiwanie przebiegu opłaca się podwójnie.
- 2026-11-12: Fat Boy 2025–2026 (117) na Facebooku kosztuje 22 000–25 000 USD. Do 11 000 USD praktycznie się nie trafia, ale zostaje w kryteriach na życzenie użytkownika.

- 2026-11-12: Użytkownik ustawił limit 15 000 mil. Odpadły Ormond Beach (31 tys.) i Nellysford (26 tys.). Przy 2018–2020 i cenie do 11 000 USD przebieg zwykle przekracza 15 tys., więc oferty z niskim przebiegiem są najcenniejsze.

- 2026-11-12 (runda 2): Zapytania regionalne („Fat Boy” harley 2018 OR 2019 + 5–6 stanów) są najskuteczniejsze. Zachód (CO, UT, NV, OR, WA, ID) dał 3 nowe pasujące oferty, w tym 2018 FLFBS za 10 500 USD z 1 tys. mil w Rathdrum, ID. Trzeba przejść wszystkie grupy stanów, nie tylko Midwest.
- 2026-11-12 (runda 2): Najlepsze fragmenty pochodzą ze stron kategorii miast (`/marketplace/<miasto>/harley-davidson/`), bo podają cenę, „price drop” i przebieg („1K miles”, „6.3K miles”). Zapytania celowane „<model> <miasto> miles” znalazły przebieg w 3 z 3 przypadków.
- 2026-11-12 (runda 2): Ta sama oferta może mieć w indeksie różne miasta (Vernon Rockville albo Madison, CT), bo Facebook podaje lokalizację przybliżoną. Przed dodaniem nowej oferty porównaj rocznik, cenę i przebieg.

- 2026-11-12: Ranking liczy koszt całkowity z dowozem (0,60 USD za milę powyżej 300 mil). Oferta z Idaho za 10 500 USD kosztuje realnie ~11 600 USD, czyli więcej niż oferta z Michigan za 10 000 USD. Zawsze wpisuj `distance_mi`.

- 2026-11-12 (runda 3): Oferty z „related” bez linku najlepiej doszukiwać zbiorczo, jednym zapytaniem z 2–3 miastami, np. `site:facebook.com/marketplace "2018 Harley-Davidson Fat Boy" Gautier OR "Cape Coral" OR Clover`. Strony kategorii tych miast podały przebieg trzech ofert naraz. Kopie ogłoszeń na stronach-lustrach (fleetpainting.com, capracycling.com) zawierają pełny opis, dzięki czemu potwierdzono 114 w Caledonii. Ogólne zapytania z todo o cenę („<rocznik> Fat Boy 114 price facebook marketplace”) dały 0 trafień na 6 prób.
- 2026-11-12 (runda 3): Pułapka: ta sama oferta ma w indeksie różne ceny, np. Rathdrum 13 000/11 900/10 500, a Seymour 15 000/13 500/12 000/10 000. Niższa cena to zwykle nowsza obniżka, ale trzeba to opisać w notatce. Parser przypisuje cenę i przebieg z sąsiednich ogłoszeń w „related”: Seymour dostał 8000 mil od Fat Boba, a Hartford cenę z Grand Rapids. Wynik `parse` zawsze sprawdzaj ręcznie.
- 2026-11-12 (runda 3): Ograniczenia silnika: raport zapisuje się pod samą datą, więc drugi przebieg tego samego dnia nadpisuje `reports/RRRR-MM-DD.md`. Oferta z watchlisty, która dostała cenę (Killen, 29 000 USD), zostaje w watchliście i dalej figuruje w todo. Przebieg za 49 zapytań kosztuje ~350 kredytów, a po nim Firecrawl ostrzega o niskim saldzie.

## Pomysły na eksperymenty
- Grupy stanów jeszcze nieprzeszukane: południe (LA, MS, AR, AL, GA, SC), Nowa Anglia (ME, VT, RI) i Plains (NE, SD, ND, MT, WY, NM)
- „<miasto> harley-davidson Fat Boy 114 miles” dla stanów, gdzie jeszcze nic nie znaleziono (np. NJ, MA, MD, TN, MO)
- „fatboy 114” jako jedno słowo plus nazwa stanu
- Zapytania o konkretne kolory i edycje, np. „115th Anniversary” 2018 albo „30th Anniversary” 2020
- Strony kategorii miast: `site:facebook.com/marketplace "<miasto>" harley-davidson "Fat Boy 114"`
