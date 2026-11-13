---
name: fat-boy-scout
description: Uruchamia przebieg Fat Boy Scout – wyszukiwanie Harley-Davidson Fat Boy (2018+, do 11 000 USD, do 15 000 mil) na Facebook Marketplace w całych USA – i pokazuje raport. Użyj, gdy użytkownik wpisze /fat-boy-scout, poprosi o „raport Fat Boy Scout”, „nowe Fat Boye”, „sprawdź Fat Boye” albo o spadki cen.
---

# Fat Boy Scout – jeden przebieg

1. Uruchom `python3 fat-boy-scout/scout.py begin`. Jeśli wynik ma `"resumed": true`, to wznowienie przerwanego
   przebiegu – powiedz o tym użytkownikowi jednym zdaniem (ile zapytań wykonano, ile zostało).
2. Uruchom agenta **fat-boy-scout** (narzędzie Agent, `subagent_type: "fat-boy-scout"`) z poleceniem:
   „Przebieg <run_id> (wznowiony: tak/nie). Działaj zgodnie ze swoją procedurą: tylko zapytania z `remaining`, `record`
   po każdym zapytaniu, szerokie trafienia potwierdzaj cytatem z opisu, `todo`, `finish`, `improve --apply`, lekcje,
   commit i push. Przy braku kredytów zapisz błąd i zakończ bez `finish`. Oddaj raport dosłownie oraz sumę kredytów.”
   Jeśli użytkownik podał dodatkowe życzenia, przekaż je agentowi jako jednorazowe.
3. Pokaż użytkownikowi raport dokładnie tak, jak zwrócił go agent: każdą część osobno, z wszystkimi linkami.
   Na końcu dodaj 1–2 zdania: co nowego (nowe oferty, spadki cen) i która oferta jest najlepsza według kosztu całkowitego.
4. Jeśli agent zgłosił problem (brak kredytów, błąd źródła, przebieg niedokończony), napisz to wprost: przebieg jest otwarty
   i kolejne `/fat-boy-scout` go dokończy. Nie przedstawiaj częściowych wyników jako pełnego raportu.
