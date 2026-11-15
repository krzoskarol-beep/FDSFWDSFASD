# Zasady pracy w tym repozytorium

## Narzędzia do internetu (zasada użytkownika)
- **Firecrawl nie używać** do pobierania ani czytania stron (ani do szukania).
- **Zwykłe strony** czytać przez **Jina** (serwer MCP `jina`, narzędzie `jina_reader`).
- **Strony z logowaniem, przyciskami lub dynamiczne** otwierać przez **Playwright** (serwer MCP `playwright`).
- **Szukanie w internecie:** wbudowane **WebSearch**.
- **Przed użyciem narzędzia napisać krótko, którego się używa i dlaczego.**

Serwery `jina` i `playwright` są zdefiniowane w `.mcp.json` (ładują się po zatwierdzeniu na starcie sesji).
Klucz Jina pochodzi ze zmiennej środowiskowej `JINA_API_KEY` – nigdy nie wpisywać go do plików.
Facebook wymaga logowania: nie logować się za użytkownika i nie obchodzić zabezpieczeń; Playwright otwiera
Facebooka tylko w zalogowanej przeglądarce użytkownika (tryb `--extension`).

## Fat Boy Scout
Agent `.claude/agents/fat-boy-scout.md`, skill `/fat-boy-scout`, kod w `fat-boy-scout/`.
Testy: `python3 -m unittest fat-boy-scout/test_scout.py fat-boy-scout/test_aimm.py`.
