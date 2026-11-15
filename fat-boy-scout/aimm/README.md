# ai-marketplace-monitor (aimm) + Fat Boy Scout

aimm (https://github.com/BoPeng/ai-marketplace-monitor, AGPL-3.0, sprawdzona wersja 0.10.16) przegląda Facebook Marketplace
w prawdziwej przeglądarce na **Twoim komputerze** i otwiera każde ogłoszenie. Daje bezpośrednie linki, pełny opis, cenę,
lokalizację i sprzedawcę, czyli dane, których indeks wyszukiwarki nie zapewnia.

**Ryzyko:** aimm szuka tylko po zalogowaniu na Twoje konto Facebooka. Automatyczne przeglądanie Marketplace jest niezgodne
z regulaminem Facebooka i może skończyć się blokadą konta. Decyzja należy do Ciebie. Konfiguracja szuka rzadko (co 12 godzin),
żeby to ryzyko ograniczyć.

## Uruchomienie (Windows / macOS / Linux)
1. Python 3.10+ i: `pip install ai-marketplace-monitor`, potem `playwright install chromium`
2. Login i hasło tylko w zmiennych środowiskowych, nie w pliku:
   - PowerShell: `$env:FACEBOOK_USERNAME="..."; $env:FACEBOOK_PASSWORD="..."`
   - macOS/Linux: `export FACEBOOK_USERNAME=... FACEBOOK_PASSWORD=...`
3. Z katalogu repozytorium: `aimm --config fat-boy-scout/aimm/config.toml`
   Otworzy się przeglądarka. Gdy Facebook poprosi o CAPTCHA albo potwierdzenie na telefonie, zrób to ręcznie.
4. Gdy aimm zbierze oferty: `python fat-boy-scout/aimm/import_aimm.py --dry-run` (podgląd raportu), a potem bez `--dry-run`
   (scalenie z historią: spadki cen, ponowne wystawienia, sekcja „Do sprawdzenia”).
5. Zrób commit i push zmian w `fat-boy-scout/`, żeby kolejne `/fat-boy-scout` w chmurze widziało te oferty.

Opcjonalnie: powiadomienia na telefon (ntfy) w sekcji `[user.me]` pliku `config.toml`.

## Co sprawdzono w chmurze (bez dostępu do Facebooka)
- Kod pakietu nie zawiera obchodzenia zabezpieczeń (stealth, rozwiązywanie CAPTCHA). Łączy się z facebook.com, PyPI
  (sprawdzanie aktualizacji) i wyłącznie z usługami AI albo powiadomień, które sam skonfigurujesz.
- `config.toml` przechodzi walidację wbudowaną w aimm (`Config([...])`).
- `import_aimm.py` przetestowany na pamięci zbudowanej funkcją aimm `Listing.to_cache` z ogłoszeniami SYMULOWANYMI.
