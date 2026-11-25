# Godziny Pracy — wersja na iPhone'a (aplikacja webowa)

Ta sama aplikacja co na Androidzie (`hours-app/`), działająca w Safari na iPhonie.
Po dodaniu do ekranu początkowego ma własną ikonę, otwiera się na pełnym ekranie i
**działa bez internetu**. Bez App Store, bez konta deweloperskiego.

Adres (po włączeniu GitHub Pages, patrz niżej): **https://krzoskarol-beep.github.io/FDSFWDSFASD/**

## Instalacja na iPhonie

1. Otwórz adres w **Safari** (nie w innej przeglądarce).
2. Stuknij **Udostępnij** (kwadrat ze strzałką) → **Do ekranu początkowego** → **Dodaj**.
3. Otwieraj aplikację ikoną „Godziny” z ekranu początkowego.

## Co potrafi

Wszystko co wersja na Androida 1.7: Clock In / Clock Out z licznikiem, tydzień (godziny i
wypłata brutto, stawka domyślnie $34/h, bez nadgodzin), edycja wpisów (data, godziny,
−1 h / −15 min / +15 min / +1 h, przerwa), dodawanie ręczne, usuwanie dnia z „Cofnij”,
**raport tygodnia i raport miesiąca** (kopiuj / udostępnij), ustawienia (stawka, początek
tygodnia, wygląd jasny / ciemny), kopia CSV.

## Dane

- Wpisy są **tylko w tym telefonie** (pamięć Safari dla tej aplikacji). Nic nie jest wysyłane.
- Rób co jakiś czas **kopię CSV** (Ustawienia → Eksportuj → „Zachowaj w Plikach”).
  Usunięcie ikony lub danych Safari kasuje wpisy.
- Plik CSV jest wspólny z Androidem: kopię z telefonu z Androidem przywrócisz na iPhonie
  (Ustawienia → Przywróć) i odwrotnie.

## Zgodność z wersją na Androida (sprawdzana automatycznie)

`core.js` to ta sama logika co `WorkMath` / `Report` / `Csv` z Androida. Testy (`npm test`)
wczytują próbkę 12 tygodni wygenerowaną przez aplikację na Androida i sprawdzają:
sumy tygodni co do minuty i centa, **identyczny** eksport CSV (bajt w bajt) oraz **identyczny**
tekst raportu tygodnia i miesiąca. CI Androida pilnuje, żeby te pliki były aktualne.

```bash
cd hours-web
npm test                                   # logika (strefa America/New_York jak próbka)
TZ=America/New_York node test/e2e.mjs      # cała aplikacja w Chromium z ekranem iPhone'a 13
```

## Publikacja (jednorazowo)

1. Scal PR z tą wersją do gałęzi domyślnej.
2. Na GitHubie: **Settings → Pages → Build and deployment → Source: „GitHub Actions”**.
3. Actions → „Strona – Godziny Pracy (iPhone)” → **Run workflow** (potem publikuje się sama
   po każdej zmianie w `hours-web/`).

Nowa wersja dociera do telefonu przy następnym otwarciu aplikacji z internetem.
