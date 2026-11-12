---
name: fat-boy-scout
description: Uruchamia przebieg Fat Boy Scout – wyszukiwanie Harley-Davidson Fat Boy (2018+, do 11 000 USD, do 15 000 mil) na Facebook Marketplace w całych USA – i pokazuje raport. Użyj, gdy użytkownik wpisze /fat-boy-scout, poprosi o „raport Fat Boy Scout”, „nowe Fat Boye”, „sprawdź Fat Boye” albo o spadki cen.
---

# Fat Boy Scout – jeden przebieg

1. Ustal dzisiejszą datę (RRRR-MM-DD). Jeśli przebieg z tą datą już istnieje w `fat-boy-scout/state.json` (pole `runs`),
   użyj `run_id` z dopiskiem godziny, np. `2026-11-19-18`.
2. Uruchom agenta **fat-boy-scout** (narzędzie Agent, `subagent_type: "fat-boy-scout"`) z poleceniem:
   „Zrób pełny przebieg na dzień <data> zgodnie ze swoją procedurą: plan, eksperymenty, doszukanie braków ze `scout.py todo`,
   `scout.py check`, `scout.py run`, `scout.py improve --apply`, lekcje w playbooku, commit i push. Oddaj raport dosłownie.”
   Jeśli użytkownik podał dodatkowe życzenia (np. tylko Midwest, inny limit), przekaż je agentowi jako jednorazowe.
3. Pokaż użytkownikowi raport dokładnie tak, jak zwrócił go agent: każdą część osobno, z wszystkimi linkami.
   Na końcu dodaj 1–2 zdania: co nowego (nowe oferty, spadki cen) i która oferta jest najlepsza według kosztu całkowitego.
4. Jeśli agent zgłosił problem (np. mało wyników, nieudany skan), napisz to wprost i nie przedstawiaj raportu jako pełnego.
