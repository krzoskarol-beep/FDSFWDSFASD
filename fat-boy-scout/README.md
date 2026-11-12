# Fat Boy Scout

Agent wyszukujący ogłoszenia Harley-Davidson Fat Boy 114 i Fat Bob 114 (2018+) oraz Indian Challenger do 11 000 USD
w IL, WI, IN, MI, IA i OH, z okazjami Honda Africa Twin i Gold Wing przy okazji.

**Uruchomienie:** w Claude Code napisz „uruchom Fat Boy Scout” (agent `.claude/agents/fat-boy-scout.md`).

| Plik | Do czego służy |
|---|---|
| `config.json` | kryteria, kolejność stanów, plan wyszukiwań, orientacyjne ceny rynkowe do rankingu (edytuj je swobodnie) |
| `scout.py` | silnik: kryteria, VIN, scalanie z historią, spadki cen, zniknięcia, ranking, raport w częściach |
| `runs/RRRR-MM-DD.json` | surowe obserwacje agenta z jednego przebiegu |
| `state.json` | historia wszystkich ofert (ceny, daty, status) i lista odrzuconych |
| `reports/RRRR-MM-DD.md` | gotowe raporty |
| `test_scout.py` | testy silnika: `python3 -m unittest fat-boy-scout/test_scout.py` |

Przydatne polecenia:
```
python3 fat-boy-scout/scout.py status           # co jest śledzone
python3 fat-boy-scout/scout.py plan             # lista wyszukiwań
python3 fat-boy-scout/scout.py vin 1HD1YLK18JC024906
python3 fat-boy-scout/scout.py run fat-boy-scout/runs/2026-11-19.json --dry-run
```

**Ograniczenie:** Facebook Marketplace wymaga logowania. Agent przeszukuje go tylko przez indeks wyszukiwarki,
a takie oferty oznacza jako niezweryfikowane.
