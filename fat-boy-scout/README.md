# Fat Boy Scout

Agent wyszukujący na **Facebook Marketplace w całych USA** ogłoszenia **Harley-Davidson Fat Boy 114** (2018+) do **11 000 USD**.
Z każdym przebiegiem sam się ulepsza: przycina martwe zapytania, dodaje skuteczne, kalibruje ceny rynkowe i zapisuje lekcje.

**Uruchomienie:** wpisz `/fat-boy-scout` albo „uruchom Fat Boy Scout” (skill `.claude/skills/fat-boy-scout`, agent `.claude/agents/fat-boy-scout.md`).

| Plik | Do czego służy |
|---|---|
| `config.json` | kryteria, zasięg, źródła, plan zapytań (aktualizowany automatycznie), ceny referencyjne |
| `playbook.md` | lekcje agenta z poprzednich przebiegów (czyta je na starcie, dopisuje na końcu) |
| `improvements.md` | dziennik automatycznych zmian planu i cen |
| `scout.py` | silnik: kryteria, scalanie z historią, spadki cen, duplikaty, ranking kosztu całkowitego, raport, `improve`, `parse` |
| `geo.py` | szacunkowa odległość od Des Plaines (środki stanów, bez internetu) |
| `raw/` | surowe wyniki wyszukiwania dla parsera |
| `runs/RRRR-MM-DD.json` | surowe obserwacje agenta z jednego przebiegu |
| `state.json` | historia ofert, statystyki zapytań, odrzucone |
| `reports/RRRR-MM-DD.md` | gotowe raporty |
| `archive/` | dane z poprzedniej konfiguracji (Midwest, Cycle Trader, kilka modeli) |

Przebieg (te polecenia wykonuje agent przy `/fat-boy-scout`; postęp zapisywany po każdym zapytaniu):
```
python3 fat-boy-scout/scout.py begin                      # nowy przebieg albo wznowienie przerwanego
python3 fat-boy-scout/scout.py record <run_id> q.json     # po KAŻDYM zapytaniu: wyniki + kredyty
python3 fat-boy-scout/scout.py remaining <run_id>         # co zostało z planu
python3 fat-boy-scout/scout.py finish <run_id>            # walidacja, scalenie z historią, raport
```

Pozostałe:
```
python3 fat-boy-scout/scout.py status
python3 fat-boy-scout/scout.py todo            # czego brakuje w aktywnych ofertach + gotowe zapytania
python3 fat-boy-scout/scout.py check fat-boy-scout/runs/2026-11-19.json   # walidacja przed uruchomieniem
python3 fat-boy-scout/scout.py plan
python3 fat-boy-scout/scout.py run fat-boy-scout/runs/2026-11-19.json
python3 fat-boy-scout/scout.py improve --apply
python3 fat-boy-scout/scout.py parse fat-boy-scout/raw/2026-11-19.json   # wyniki wyszukiwania → kandydaci
python3 fat-boy-scout/scout.py recall moje_linki.txt   # test skuteczności
python3 -m unittest fat-boy-scout/test_scout.py
```

**Test skuteczności:** znajdź ręcznie na Marketplace kilka (np. 10) pasujących ofert i wklej ich linki do pliku, po jednym w linii.
Po zwykłym przebiegu `recall` pokaże, ile z nich Scout znalazł sam (np. 7/10) i które przeoczył.

**Ograniczenie:** ogłoszenia Facebooka wymagają logowania, więc agent korzysta z indeksu wyszukiwarki.
Ceny i dostępność trzeba potwierdzić po kliknięciu w link.

**Raport** zawiera wszystkie potwierdzone oferty (z bezpośrednim linkiem), sekcję „Do sprawdzenia” (co ustalono, czego brakuje),
zmiany cen z datami (także wejście w limit z ceny powyżej 11 000 USD), ponowne wystawienia tego samego motocykla
(VIN albo ≥3 zgodne cechy, oba linki) i pokrycie stanów: znaleziono oferty / sprawdzono, zero trafień / błąd lub blokada / jeszcze nie sprawdzono.

**Symulacja:** `python3 fat-boy-scout/sim/symulacja.py` przechodzi begin → record → przerwanie → wznowienie → finish
na zmyślonych danych w osobnym katalogu i zapisuje `sim/przykladowy_raport.md` (oznaczony jako DANE SYMULOWANE).
